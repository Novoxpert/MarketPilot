"""
Quality Assurance Stage - Basic data quality checks
"""

from typing import Dict, Any, List
from marketpilot.data_farm.stages.base_stage import BaseStage
from marketpilot.utils.logger import log_event


class QualityAssuranceStage(BaseStage):
    """Perform basic quality checks on data"""

    def __init__(self):
        super().__init__("quality_assurance")

    async def _process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Basic quality checks:
        1. Symbol exists
        2. Data payload not empty
        3. Has timestamp field
        """
        unique_data = data.get("unique_data", [])

        # Get quality threshold from config
        config = data.get("config", {})
        quality_threshold = config.get("quality", {}).get("quality_threshold", 0.95)

        validated_records = []
        qa_passed = 0
        qa_failed = 0
        issues_summary = []

        for record in unique_data:
            issues = self._check_record(record)
            
            if issues:
                qa_failed += 1
                issues_summary.append({
                    "symbol": record.get("symbol"),
                    "schema_type": record.get("schema_type"),
                    "issues": issues,
                })
            else:
                qa_passed += 1
                validated_records.append(record)

        # Calculate pass rate
        total = len(unique_data)
        pass_rate_value = (qa_passed / total) if total > 0 else 0
        pass_rate = f"{(pass_rate_value * 100):.1f}%"
        threshold_met = pass_rate_value >= quality_threshold

        log_event(
            stage=self.stage_name,
            block="quality_assurance",
            level="INFO" if threshold_met else "WARNING",
            msg=f"QA: {qa_passed} passed, {qa_failed} failed ({pass_rate})",
            extra={
                "qa_passed": qa_passed,
                "qa_failed": qa_failed,
                "pass_rate": pass_rate,
                "threshold_met": threshold_met,
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
            "issues": issues_summary[:10],  # Only keep first 10 for summary
            "total_records": total,
        }
        return data

    def _check_record(self, record: Dict[str, Any]) -> List[str]:
        """
        Check record for basic quality issues
        
        Returns: List of issues (empty if no issues)
        """
        issues = []
        record_data = record.get("data", {})
        
        # Check 1: Symbol exists
        if not record.get("symbol"):
            issues.append("missing_symbol")
        
        # Check 2: Data payload not empty
        if not record_data or len(record_data) == 0:
            issues.append("empty_data")
        
        # Check 3: Has timestamp
        timestamp_fields = [
            "timestamp", "candle_time", "releasedAt",  "date"
        ]
        has_timestamp = any(
            field in record_data and record_data[field]
            for field in timestamp_fields
        )
        if not has_timestamp:
            issues.append("missing_timestamp")
        
        return issues