
"""
NaN Processing Stage - Handle missing values
Enhanced to handle news data properly
"""

from typing import Dict, Any
import math
from marketpilot.data_farm.stages.base_stage import BaseStage
from marketpilot.utils.logger import log_event


class NaNProcessingStage(BaseStage):
    """Process and handle NaN/missing values"""

    def __init__(self):
        super().__init__("nan_processing")

    async def _process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process NaN values in raw data"""

        # Validate input shape
        if not isinstance(data, dict):
            raise ValueError("Input to NaNProcessingStage must be a dict")

        if "raw_data" not in data:
            raise ValueError("Missing required key 'raw_data' in pipeline data")

        raw_data = data.get("raw_data")
        if not isinstance(raw_data, list):
            raise ValueError("'raw_data' must be a list of records")

        nan_count = 0
        processed_records = []

        for idx, record in enumerate(raw_data):
            if not isinstance(record, dict):
                raise ValueError(
                    f"Each record in 'raw_data' must be a dict (index={idx})"
                )

            # Expect 'data' field to exist and be a dict
            if "data" not in record or not isinstance(record["data"], dict):
                raise ValueError(
                    f"Record at index {idx} is missing 'data' dict field or it is not a dict"
                )

            record_data = record["data"]
            schema_type = record.get("schema_type", "unknown")

            # Process based on schema type
            if schema_type == "price":
                nan_count += self._process_price_nans(record_data, record, idx)
            elif schema_type == "news":
                nan_count += self._process_news_nans(record_data, record, idx)
            elif schema_type == "fundamental":
                nan_count += self._process_fundamental_nans(record_data, record, idx)
            else:
                # Generic processing for unknown types
                nan_count += self._process_generic_nans(record_data, record, idx)

            processed_records.append(record)

        log_event(
            stage=self.stage_name,
            block="nan_processing",
            level="INFO",
            msg=f"Processed {nan_count} NaN values",
            extra={"nan_count": nan_count},
        )

        data["processed_data"] = processed_records
        data["nan_stats"] = {"nan_count": nan_count}
        return data

    def _process_price_nans(
        self, record_data: Dict[str, Any], record: Dict[str, Any], idx: int
    ) -> int:
        """Process NaN values in price data"""
        nan_count = 0
        numeric_fields = ["open", "high", "low", "close", "volume"]

        for key in numeric_fields:
            if key in record_data:
                value = record_data[key]
                if value is None or (isinstance(value, float) and math.isnan(value)):
                    nan_count += 1
                    record_data[key] = 0
                    log_event(
                        stage=self.stage_name,
                        block="nan_processing",
                        level="DEBUG",
                        msg=f"NaN replaced in price field: {key}",
                        extra={
                            "symbol": record.get("symbol"),
                            "adapter_id": record.get("adapter_id"),
                            "record_index": idx,
                        },
                    )

        return nan_count

    def _process_news_nans(
        self, record_data: Dict[str, Any], record: Dict[str, Any], idx: int
    ) -> int:
        """Process NaN values in news data - mostly no action needed for strings"""
        nan_count = 0

        # For news, we mainly check numeric fields like mapping_confidence
        numeric_fields = ["mapping_confidence", "asset_count"]

        for key in numeric_fields:
            if key in record_data:
                value = record_data[key]
                if value is None or (isinstance(value, float) and math.isnan(value)):
                    nan_count += 1
                    # Set default values
                    if key == "mapping_confidence":
                        record_data[key] = 0.5
                    elif key == "asset_count":
                        record_data[key] = 0

                    log_event(
                        stage=self.stage_name,
                        block="nan_processing",
                        level="DEBUG",
                        msg=f"NaN replaced in news field: {key}",
                        extra={
                            "symbol": record.get("symbol"),
                            "adapter_id": record.get("adapter_id"),
                            "record_index": idx,
                        },
                    )

        # Clean empty strings in important text fields
        text_fields = ["title", "subtitle", "source", "source_name"]
        for key in text_fields:
            if key in record_data and record_data[key] == "":
                record_data[key] = None

        return nan_count

    def _process_fundamental_nans(
        self, record_data: Dict[str, Any], record: Dict[str, Any], idx: int
    ) -> int:
        """Process NaN values in fundamental data"""
        nan_count = 0

        # Check value field
        if "value" in record_data:
            value = record_data["value"]
            if value is None or (isinstance(value, float) and math.isnan(value)):
                nan_count += 1
                record_data["value"] = 0
                log_event(
                    stage=self.stage_name,
                    block="nan_processing",
                    level="DEBUG",
                    msg="NaN replaced in fundamental value field",
                    extra={
                        "symbol": record.get("symbol"),
                        "adapter_id": record.get("adapter_id"),
                        "record_index": idx,
                    },
                )

        return nan_count

    def _process_generic_nans(
        self, record_data: Dict[str, Any], record: Dict[str, Any], idx: int
    ) -> int:
        """Generic NaN processing for unknown types"""
        nan_count = 0

        for key, value in list(record_data.items()):
            if value is None or (isinstance(value, float) and math.isnan(value)):
                # Skip string fields and complex objects
                if isinstance(value, (dict, list)):
                    continue

                nan_count += 1
                record_data[key] = 0
                log_event(
                    stage=self.stage_name,
                    block="nan_processing",
                    level="DEBUG",
                    msg=f"NaN replaced in field: {key}",
                    extra={
                        "symbol": record.get("symbol"),
                        "adapter_id": record.get("adapter_id"),
                        "record_index": idx,
                    },
                )

        return nan_count