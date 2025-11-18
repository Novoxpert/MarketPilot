"""
Quality Assurance Stage - Validate data quality with configurable thresholds
"""

from typing import Dict, Any, List
from marketpilot.data_farm.stages.base_stage import BaseStage
from marketpilot.utils.logger import log_event


class QualityAssuranceStage(BaseStage):
    """Perform quality checks on data"""

    def __init__(self):
        super().__init__("quality_assurance")

    async def _process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform quality assurance checks"""
        unique_data = data.get("unique_data", [])

        # Get quality config from pipeline config
        config = data.get("config", {})
        quality_config = config.get("quality", {})
        quality_threshold = quality_config.get("quality_threshold", 0.95)
        validation_rules = quality_config.get("validation_rules", {})

        validated_records = []
        qa_passed = 0
        qa_failed = 0
        qa_issues_list = []

        for record in unique_data:
            record_data = record.get("data", {})
            schema_type = record.get("schema_type", "unknown")
            qa_issues: List[str] = []

            # Check 1: Symbol exists
            if "symbol" not in record or not record.get("symbol"):
                qa_issues.append("Missing symbol")

            # Check 2: Adapter ID exists
            if "adapter_id" not in record or not record.get("adapter_id"):
                qa_issues.append("Missing adapter_id")

            # Check 3: Data payload exists and is not empty
            if not record_data or len(record_data) == 0:
                qa_issues.append("Empty data payload")

            # Check 4: Timestamp field exists (check common variations)
            timestamp_fields = [
                "timestamp",
                "candle_time",
                "published_at_utc",
                "date_utc",
                "date",
                "datetime",
                "time",
            ]
            has_timestamp = any(field in record_data for field in timestamp_fields)
            if not has_timestamp:
                qa_issues.append("Missing timestamp field")

            # Type-specific validation based on config rules
            rules_for_type = validation_rules.get(schema_type, [])

            if schema_type == "price":
                qa_issues.extend(self._validate_price_data(record_data, rules_for_type))
            elif schema_type == "news":
                qa_issues.extend(self._validate_news_data(record_data, rules_for_type))
            elif schema_type == "fundamental":
                qa_issues.extend(
                    self._validate_fundamental_data(record_data, rules_for_type)
                )

            # Record result
            if qa_issues:
                qa_failed += 1
                qa_issues_list.append(
                    {
                        "symbol": record.get("symbol"),
                        "adapter_id": record.get("adapter_id"),
                        "schema_type": schema_type,
                        "issues": qa_issues,
                    }
                )
                log_event(
                    stage=self.stage_name,
                    block="quality_assurance",
                    level="WARNING",
                    msg="QA issues found",
                    extra={
                        "symbol": record.get("symbol"),
                        "adapter_id": record.get("adapter_id"),
                        "schema_type": schema_type,
                        "issues": qa_issues,
                    },
                )
            else:
                qa_passed += 1
                validated_records.append(record)

        total_records = len(unique_data)
        pass_rate_value = (qa_passed / total_records) if total_records > 0 else 0
        pass_rate = f"{(pass_rate_value * 100):.1f}%"

        # Check against configured threshold
        threshold_met = pass_rate_value >= quality_threshold

        log_event(
            stage=self.stage_name,
            block="quality_assurance",
            level="INFO" if threshold_met else "WARNING",
            msg=f"QA complete: {qa_passed} passed, {qa_failed} failed ({pass_rate} pass rate)",
            extra={
                "qa_passed": qa_passed,
                "qa_failed": qa_failed,
                "pass_rate": pass_rate,
                "total_records": total_records,
                "quality_threshold": quality_threshold,
                "threshold_met": threshold_met,
            },
        )

        if not threshold_met:
            log_event(
                stage=self.stage_name,
                block="quality_assurance",
                level="WARNING",
                msg=f"Quality threshold not met: {pass_rate} < {quality_threshold*100:.1f}%",
                extra={
                    "pass_rate": pass_rate_value,
                    "threshold": quality_threshold,
                },
            )

        data["validated_data"] = validated_records
        data["qa_stats"] = {
            "qa_passed": qa_passed,
            "qa_failed": qa_failed,
            "pass_rate": pass_rate,
            "pass_rate_value": pass_rate_value,
            "quality_threshold": quality_threshold,
            "threshold_met": threshold_met,
            "issues": qa_issues_list,
            "total_records": total_records,
        }
        return data

    def _validate_price_data(
        self, record_data: Dict[str, Any], rules: List[str]
    ) -> List[str]:
        """Validate price-specific data based on configured rules"""
        issues = []

        # If no rules specified, use defaults
        if not rules:
            rules = ["no_nan_values", "volume_consistency"]

        # Required fields for price data
        if "no_nan_values" in rules:
            required_price_fields = ["open", "high", "low", "close", "volume"]
            for field in required_price_fields:
                if field not in record_data or record_data[field] is None:
                    issues.append(f"Missing or null required price field: {field}")

        # Volume validation
        if "volume_consistency" in rules and "volume" in record_data:
            try:
                volume = record_data["volume"]
                if volume is not None:
                    vol_value = float(volume)
                    if vol_value < 0:
                        issues.append("Negative volume")
            except (ValueError, TypeError):
                issues.append("Invalid volume value")

        # Price consistency: high >= low
        try:
            if "high" in record_data and "low" in record_data:
                high = float(record_data["high"])
                low = float(record_data["low"])
                if high < low:
                    issues.append("High price is less than low price")
        except (ValueError, TypeError):
            pass  # Already caught above

        return issues

    def _validate_news_data(
        self, record_data: Dict[str, Any], rules: List[str]
    ) -> List[str]:
        """Validate news-specific data based on configured rules"""
        issues = []

        if not rules:
            rules = ["no_duplicates", "content_quality"]

        # Check for title or content
        if "content_quality" in rules:
            if "title" not in record_data and "content" not in record_data:
                issues.append("Missing both title and content")

        # Check for source
        if "source" not in record_data:
            issues.append("Missing news source")

        return issues

    def _validate_fundamental_data(
        self, record_data: Dict[str, Any], rules: List[str]
    ) -> List[str]:
        """Validate fundamental-specific data based on configured rules"""
        issues = []

        # Check for metric and value
        if "metric" not in record_data:
            issues.append("Missing metric name")

        if "value" not in record_data:
            issues.append("Missing metric value")

        return issues
