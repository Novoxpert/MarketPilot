"""
Quality Assurance Stage - Validate data quality
Fixed to properly validate heterogeneous data from multiple adapters
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

        validated_records = []
        qa_passed = 0
        qa_failed = 0
        qa_issues_list = []

        for record in unique_data:
            record_data = record.get("data", {})
            qa_issues: List[str] = []

            # Check 1: Symbol exists (at record level, not in data)
            if "symbol" not in record or not record.get("symbol"):
                qa_issues.append("Missing symbol")

            # Check 2: Adapter ID exists
            if "adapter_id" not in record or not record.get("adapter_id"):
                qa_issues.append("Missing adapter_id")

            # Check 3: Data payload exists and is not empty
            if not record_data or len(record_data) == 0:
                qa_issues.append("Empty data payload")

            # Check 4: Timestamp field exists (check common variations)
            timestamp_fields = ["timestamp", "date", "datetime", "time"]
            has_timestamp = any(field in record_data for field in timestamp_fields)
            if not has_timestamp:
                qa_issues.append("Missing timestamp field")

            # Check 5: Data type validation for price data
            if "open" in record_data or "close" in record_data:
                try:
                    # Validate numeric price fields
                    for price_field in ["open", "high", "low", "close"]:
                        if price_field in record_data:
                            price_value = record_data[price_field]
                            if price_value is not None:
                                float(price_value)  # Will raise ValueError if invalid
                                
                                # Check for negative prices
                                if float(price_value) < 0:
                                    qa_issues.append(f"Negative price in {price_field}")
                except (ValueError, TypeError) as e:
                    qa_issues.append(f"Invalid numeric value: {str(e)}")

            # Check 6: Volume validation (if present)
            if "volume" in record_data:
                try:
                    volume = record_data["volume"]
                    if volume is not None:
                        vol_value = float(volume)
                        if vol_value < 0:
                            qa_issues.append("Negative volume")
                except (ValueError, TypeError):
                    qa_issues.append("Invalid volume value")

            # Record result
            if qa_issues:
                qa_failed += 1
                qa_issues_list.append(
                    {
                        "symbol": record.get("symbol"),
                        "adapter_id": record.get("adapter_id"),
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
                        "issues": qa_issues,
                    },
                )
            else:
                qa_passed += 1
                validated_records.append(record)

        pass_rate = (
            f"{(qa_passed / len(unique_data) * 100):.1f}%"
            if unique_data
            else "0%"
        )

        log_event(
            stage=self.stage_name,
            block="quality_assurance",
            level="INFO",
            msg=f"QA complete: {qa_passed} passed, {qa_failed} failed",
            extra={
                "qa_passed": qa_passed,
                "qa_failed": qa_failed,
                "pass_rate": pass_rate,
                "total_records": len(unique_data),
            },
        )

        data["validated_data"] = validated_records
        data["qa_stats"] = {
            "qa_passed": qa_passed,
            "qa_failed": qa_failed,
            "pass_rate": pass_rate,
            "issues": qa_issues_list,
            "total_records": len(unique_data),
        }
        return data