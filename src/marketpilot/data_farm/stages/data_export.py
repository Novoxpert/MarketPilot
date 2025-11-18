"""
Data Export Stage - Export processed data with Asset-First structure
Organizes output by symbol (asset)
"""

from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
import json
import yaml
import re
from collections import defaultdict
from marketpilot.data_farm.stages.base_stage import BaseStage
from marketpilot.utils.logger import log_event


class DataExportStage(BaseStage):
    """Export validated data to Asset-First directory structure"""

    def __init__(self):
        super().__init__("data_export")

    def _sanitize_symbol_for_path(self, symbol: str) -> str:
        """
        Sanitize symbol name for use as directory/file name
        Replaces characters that are invalid in Windows/Unix paths

        Args:
            symbol: Original symbol (e.g., "BINANCE:BTCUSDT.P")

        Returns:
            Sanitized symbol (e.g., "BINANCE_BTCUSDT_P")
        """
        # Replace invalid characters with underscore
        # Windows invalid chars: < > : " / \ | ? *
        # We'll also replace dots for consistency
        sanitized = re.sub(r'[<>:"/\\|?*.]', "_", symbol)

        # Remove any double underscores that might have been created
        sanitized = re.sub(r"_+", "_", sanitized)

        # Remove leading/trailing underscores
        sanitized = sanitized.strip("_")

        return sanitized

    async def _process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Export data to Asset-First directory structure"""
        validated_data = data.get("validated_data", [])

        if not validated_data:
            log_event(
                stage=self.stage_name,
                block="data_export",
                level="WARNING",
                msg="No validated data to export",
            )
            data["export_stats"] = {
                "exported_files": [],
                "records_exported": 0,
            }
            return data

        # Get output directory from config
        config = data.get("config", {})
        output_config = config.get("output", {})

        # Get base directory (with default fallback)
        base_dir = Path(output_config.get("base_dir", "data_farm_exports"))
        base_dir.mkdir(parents=True, exist_ok=True)

        # Get export format preferences
        export_formats = output_config.get("formats", ["parquet"])
        compression = output_config.get("compression", "snappy")

        # Group records by symbol and schema_type
        grouped_data = self._group_by_symbol_and_type(validated_data)

        exported_files = []
        total_exported = 0

        # Export each symbol's data
        for symbol, types_data in grouped_data.items():
            # Sanitize symbol for directory name
            sanitized_symbol = self._sanitize_symbol_for_path(symbol)
            symbol_dir = base_dir / sanitized_symbol
            symbol_dir.mkdir(parents=True, exist_ok=True)

            # Store mapping of sanitized to original symbol in metadata
            symbol_metadata_file = symbol_dir / "symbol_info.json"
            with open(symbol_metadata_file, "w") as f:
                json.dump(
                    {
                        "original_symbol": symbol,
                        "sanitized_symbol": sanitized_symbol,
                        "exported_at": datetime.utcnow().isoformat(),
                    },
                    f,
                    indent=2,
                )

            for schema_type, records in types_data.items():
                try:
                    # Determine file format based on schema type and config
                    if "parquet" in export_formats:
                        if schema_type == "price":
                            export_file = symbol_dir / "price.parquet"
                        elif schema_type == "news":
                            export_file = symbol_dir / "news.parquet"
                        elif schema_type == "fundamental":
                            export_file = symbol_dir / "fundamentals.parquet"
                        else:
                            export_file = symbol_dir / f"{schema_type}.parquet"

                        self._export_to_parquet(records, export_file, compression)
                    else:
                        # Fallback to JSON
                        if schema_type == "price":
                            export_file = symbol_dir / "price.json"
                        elif schema_type == "news":
                            export_file = symbol_dir / "news.json"
                        elif schema_type == "fundamental":
                            export_file = symbol_dir / "fundamentals.json"
                        else:
                            export_file = symbol_dir / f"{schema_type}.json"

                        self._export_to_json(records, export_file)

                    exported_files.append(str(export_file))
                    total_exported += len(records)

                    log_event(
                        stage=self.stage_name,
                        block="data_export",
                        level="INFO",
                        msg=f"Exported {schema_type} data for {symbol}",
                        extra={
                            "symbol": symbol,
                            "sanitized_symbol": sanitized_symbol,
                            "schema_type": schema_type,
                            "records": len(records),
                            "file": str(export_file),
                            "format": (
                                "parquet" if "parquet" in export_formats else "json"
                            ),
                        },
                    )

                except Exception as e:
                    log_event(
                        stage=self.stage_name,
                        block="data_export",
                        level="ERROR",
                        msg=f"Failed to export {schema_type} for {symbol}: {str(e)}",
                        extra={
                            "symbol": symbol,
                            "schema_type": schema_type,
                            "error": str(e),
                        },
                    )

        # Create __meta__ directory for metadata
        self._create_metadata(base_dir, grouped_data, data)

        log_event(
            stage=self.stage_name,
            block="data_export",
            level="INFO",
            msg="Data export completed",
            extra={
                "total_symbols": len(grouped_data),
                "total_files": len(exported_files),
                "total_records": total_exported,
                "output_directory": str(base_dir),
            },
        )

        data["export_stats"] = {
            "exported_files": exported_files,
            "records_exported": total_exported,
            "symbols_processed": list(grouped_data.keys()),
            "output_directory": str(base_dir),
        }

        return data

    def _group_by_symbol_and_type(
        self, records: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        Group records by symbol and schema type

        Args:
            records: List of validated records

        Returns:
            Nested dict: {symbol: {schema_type: [records]}}
        """
        grouped = defaultdict(lambda: defaultdict(list))

        for record in records:
            symbol = record.get("symbol")
            schema_type = record.get("schema_type", "unknown")

            # Fallback: detect from adapter_id if schema_type not present
            if schema_type == "unknown":
                adapter_id = record.get("adapter_id", "")
                schema_type = self._detect_schema_type(adapter_id)

            if not symbol:
                log_event(
                    stage=self.stage_name,
                    block="grouping",
                    level="WARNING",
                    msg="Record missing symbol, skipping",
                    extra={"adapter_id": record.get("adapter_id")},
                )
                continue

            grouped[symbol][schema_type].append(record)

        return dict(grouped)

    def _detect_schema_type(self, adapter_id: str) -> str:
        """
        Detect schema type from adapter_id

        Args:
            adapter_id: Adapter identifier

        Returns:
            Schema type (price, news, fundamental)
        """
        adapter_lower = adapter_id.lower()

        if "price" in adapter_lower:
            return "price"
        elif "news" in adapter_lower:
            return "news"
        elif "fundamental" in adapter_lower:
            return "fundamental"
        else:
            return "unknown"

    def _export_to_parquet(
        self,
        records: List[Dict[str, Any]],
        file_path: Path,
        compression: str = "snappy",
    ):
        """
        Export records to Parquet format

        Args:
            records: List of records to export
            file_path: Output file path
            compression: Compression algorithm (snappy, gzip, etc.)
        """
        try:
            import pandas as pd

            # Flatten records for DataFrame
            flattened = []
            for record in records:
                flat_record = {
                    "symbol": record.get("symbol"),
                    "adapter_id": record.get("adapter_id"),
                    "vendor": record.get("vendor"),
                    "ingested_at": record.get("ingested_at"),
                }

                # Flatten data payload
                data_payload = record.get("data", {})
                if isinstance(data_payload, dict):
                    flat_record.update(data_payload)

                flattened.append(flat_record)

            # Create DataFrame and export
            df = pd.DataFrame(flattened)

            # Convert timestamp columns to datetime
            timestamp_cols = [
                "timestamp",
                "candle_time",
                "published_at_utc",
                "date_utc",
                "startdate",
                "enddate",
                "ingested_at",
            ]
            for col in timestamp_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce")

            # Export to Parquet with specified compression
            df.to_parquet(
                file_path, index=False, engine="pyarrow", compression=compression
            )

        except ImportError:
            log_event(
                stage=self.stage_name,
                block="export",
                level="WARNING",
                msg="pandas/pyarrow not available, falling back to JSON",
            )
            # Fallback to JSON if pandas not available
            json_path = file_path.with_suffix(".json")
            self._export_to_json(records, json_path)
        except Exception as e:
            log_event(
                stage=self.stage_name,
                block="export",
                level="ERROR",
                msg=f"Parquet export failed: {str(e)}, falling back to JSON",
                extra={"error": str(e)},
            )
            json_path = file_path.with_suffix(".json")
            self._export_to_json(records, json_path)

    def _export_to_json(self, records: List[Dict[str, Any]], file_path: Path):
        """
        Export records to JSON format

        Args:
            records: List of records to export
            file_path: Output file path
        """
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False, default=str)

    def _create_metadata(
        self, base_dir: Path, grouped_data: Dict, pipeline_data: Dict[str, Any]
    ):
        """
        Create metadata files in __meta__ directory

        Args:
            base_dir: Base export directory
            grouped_data: Grouped data by symbol
            pipeline_data: Complete pipeline data
        """
        meta_dir = base_dir / "__meta__"
        meta_dir.mkdir(parents=True, exist_ok=True)

        # 1. Schema versions
        schema_versions = {
            "created_at": datetime.utcnow().isoformat(),
            "schemas": {
                "price": "v1.0",
                "news": "v1.0",
                "fundamental": "v1.0",
            },
        }

        with open(meta_dir / "schema_versions.yaml", "w") as f:
            yaml.dump(schema_versions, f, default_flow_style=False)

        # 2. Symbol mapping (original to sanitized)
        symbol_mapping = {}
        for symbol in grouped_data.keys():
            sanitized = self._sanitize_symbol_for_path(symbol)
            symbol_mapping[symbol] = {"sanitized": sanitized, "directory": sanitized}

        with open(meta_dir / "symbol_mapping.json", "w") as f:
            json.dump(symbol_mapping, f, indent=2)

        # 3. Manifest (JSONL format)
        manifest_path = meta_dir / "manifest.jsonl"
        with open(manifest_path, "w") as f:
            for symbol, types_data in grouped_data.items():
                sanitized_symbol = self._sanitize_symbol_for_path(symbol)
                for schema_type, records in types_data.items():
                    # Determine file extension based on export format
                    config = pipeline_data.get("config", {})
                    export_formats = config.get("output", {}).get(
                        "formats", ["parquet"]
                    )
                    file_ext = "parquet" if "parquet" in export_formats else "json"

                    manifest_entry = {
                        "symbol": symbol,
                        "sanitized_symbol": sanitized_symbol,
                        "schema_type": schema_type,
                        "record_count": len(records),
                        "exported_at": datetime.utcnow().isoformat(),
                        "file": f"{sanitized_symbol}/{schema_type}.{file_ext}",
                        "format": file_ext,
                    }
                    f.write(json.dumps(manifest_entry) + "\n")

        # 4. Pipeline stats
        stats = {
            "exported_at": datetime.utcnow().isoformat(),
            "pipeline_stats": {
                "health_check": pipeline_data.get("health_check", {}),
                "fetch_summary": pipeline_data.get("fetch_summary", {}),
                "nan_stats": pipeline_data.get("nan_stats", {}),
                "alignment_stats": pipeline_data.get("alignment_stats", {}),
                "dedup_stats": pipeline_data.get("dedup_stats", {}),
                "qa_stats": pipeline_data.get("qa_stats", {}),
            },
            "total_symbols": len(grouped_data),
            "total_records": sum(
                len(records)
                for types_data in grouped_data.values()
                for records in types_data.values()
            ),
        }

        with open(meta_dir / "pipeline_stats.json", "w") as f:
            json.dump(stats, f, indent=2, default=str)

        log_event(
            stage=self.stage_name,
            block="metadata",
            level="INFO",
            msg="Metadata files created",
            extra={"meta_dir": str(meta_dir)},
        )
