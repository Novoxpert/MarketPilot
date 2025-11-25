"""
NaN Processing Stage - Handle missing values
"""

from typing import Dict, Any
import math
from marketpilot.data_farm.stages.base_stage import BaseStage
from marketpilot.utils.logger import log_event


class NaNProcessingStage(BaseStage):
    """Clean NaN and missing values from data"""

    def __init__(self):
        super().__init__("nan_processing")

    async def _process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process NaN values in raw_data
        
        Strategy:
        - Numeric fields: Replace NaN with 0
        - Text fields: Replace empty strings with None
        - Keep track of how many NaNs were fixed
        """
        raw_data = data.get("raw_data", [])
        
        if not isinstance(raw_data, list):
            raise ValueError("raw_data must be a list")

        nan_count = 0
        processed_records = []

        for record in raw_data:
            record_data = record.get("data", {})
            
            # Process NaNs in data payload
            nan_count += self._clean_nans(record_data)
            
            processed_records.append(record)

        log_event(
            stage=self.stage_name,
            block="nan_processing",
            level="INFO",
            msg=f"Cleaned {nan_count} NaN values",
            extra={"nan_count": nan_count, "records": len(processed_records)},
        )

        data["processed_data"] = processed_records
        data["nan_stats"] = {"nan_count": nan_count}
        return data

    def _clean_nans(self, record_data: Dict[str, Any]) -> int:
        """
        Clean NaN values in a record
        
        Returns: Number of NaNs cleaned
        """
        nan_count = 0
        
        for key, value in list(record_data.items()):
            # Skip nested objects and arrays
            if isinstance(value, (dict, list)):
                continue
            
            # Check for NaN or None
            is_nan = (
                value is None
                or (isinstance(value, float) and math.isnan(value))
                or value == ""
            )
            
            if is_nan:
                nan_count += 1
                # Replace with appropriate default
                if isinstance(value, (int, float)) or key in self._numeric_fields():
                    record_data[key] = 0
                else:
                    record_data[key] = None
        
        return nan_count

    def _numeric_fields(self) -> set:
        """Common numeric field names across all data types"""
        return {
            "open", "high", "low", "close", "volume",  # price
            "mapping_confidence", "asset_count",  # news
            "value", "pe_ratio", "debt_to_equity",  # fundamental
        }