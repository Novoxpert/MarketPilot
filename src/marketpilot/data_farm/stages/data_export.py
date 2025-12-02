"""
Data Export Stage - Export to Asset-First directory structure
"""

from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
import json
import re
from collections import defaultdict
from marketpilot.data_farm.stages.base_stage import BaseStage
from marketpilot.utils.logger import log_event


class DataExportStage(BaseStage):
    """Export validated data to Asset-First structure"""

    def __init__(self):
        super().__init__("data_export")

    async def _process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Export data organized by symbol"""
        validated_data = data.get("validated_data", [])

        if not validated_data:
            log_event(
                stage=self.stage_name,
                block="data_export",
                level="WARNING",
                msg="No validated data to export",
            )
            data["export_stats"] = {"exported_files": [], "records_exported": 0}
            return data

        # Get config
        config = data.get("config", {})
        base_dir = Path(config.get("output", {}).get("base_dir", "data_farm_exports"))
        base_dir.mkdir(parents=True, exist_ok=True)

        # Group by symbol and type
        grouped = self._group_by_symbol_and_type(validated_data)

        exported_files = []
        total_exported = 0

        # Export each symbol
        # types_data/price/
        for symbol, types_data in grouped.items():
            sanitized = self._sanitize_symbol(symbol)
            symbol_dir = base_dir / sanitized
            symbol_dir.mkdir(parents=True, exist_ok=True)

            # Save symbol mapping
            self._save_symbol_info(symbol_dir, symbol, sanitized)

            # Export each data type
            for schema_type, records in types_data.items():
                try:
                    export_file = symbol_dir / f"{schema_type}.parquet"
                    self._export_to_parquet(records, export_file, schema_type)
                    
                    exported_files.append(str(export_file))
                    total_exported += len(records)
                    
                    log_event(
                        stage=self.stage_name,
                        block="data_export",
                        level="INFO",
                        msg=f"Exported {schema_type} for {symbol}",
                        extra={
                            "symbol": symbol,
                            "schema_type": schema_type,
                            "records": len(records),
                            "file": str(export_file),
                        },
                    )
                except Exception as e:
                    log_event(
                        stage=self.stage_name,
                        block="data_export",
                        level="ERROR",
                        msg=f"Export failed: {str(e)}",
                        extra={"symbol": symbol, "schema_type": schema_type, "error": str(e)},
                    )

        # Create metadata
        self._create_metadata(base_dir, grouped, data)

        log_event(
            stage=self.stage_name,
            block="data_export",
            level="INFO",
            msg=f"Export complete: {len(grouped)} symbols, {total_exported} records",
            extra={
                "symbols": len(grouped),
                "files": len(exported_files),
                "records": total_exported,
            },
        )

        data["export_stats"] = {
            "exported_files": exported_files,
            "records_exported": total_exported,
            "symbols_processed": list(grouped.keys()),
            "output_directory": str(base_dir),
        }
        return data

    def _sanitize_symbol(self, symbol: str) -> str:
        """Sanitize symbol for filesystem (replace special chars with _)"""
        sanitized = re.sub(r'[<>:"/\\|?*.]', "_", symbol)
        sanitized = re.sub(r"_+", "_", sanitized)
        return sanitized.strip("_")

    def _group_by_symbol_and_type(
        self, records: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """Group records by symbol and schema_type"""
        grouped = defaultdict(lambda: defaultdict(list))
        
        for record in records:
            symbol = record.get("symbol")
            schema_type = record.get("schema_type", "unknown")
            
            if symbol:
                grouped[symbol][schema_type].append(record)
        
        return dict(grouped)

    def _save_symbol_info(self, symbol_dir: Path, original: str, sanitized: str):
        """Save symbol mapping info"""
        info_file = symbol_dir / "symbol_info.json"
        with open(info_file, "w") as f:
            json.dump({
                "original_symbol": original,
                "sanitized_symbol": sanitized,
                "exported_at": datetime.utcnow().isoformat(),
            }, f, indent=2)

    def _export_to_parquet(
        self, records: List[Dict], file_path: Path, schema_type: str
    ):
        """Export records to Parquet with proper timestamp handling"""
        try:
            import pandas as pd

            # Flatten records
            flattened = []
            for record in records:
                flat = {
                    "symbol": record.get("symbol"),
                    "adapter_id": record.get("adapter_id"),
                    "vendor": record.get("vendor"),
                    "ingested_at": record.get("ingested_at"),
                }
                
                # Add data payload
                data_payload = record.get("data", {})
                if isinstance(data_payload, dict):
                    # Handle nested structures (news assets)
                    if schema_type == "news" and "assets" in data_payload:
                        flat["assets_json"] = json.dumps(data_payload["assets"])
                        flat["asset_count"] = len(data_payload["assets"])
                        # Add other fields except assets
                        flat.update({k: v for k, v in data_payload.items() if k != "assets"})
                    else:
                        flat.update(data_payload)
                
                flattened.append(flat)

            # Create DataFrame
            df = pd.DataFrame(flattened)

            # Convert Unix timestamps (ms) to pandas datetime
            timestamp_cols = [
                "timestamp", "candle_time", "published_at_utc",
                "date_utc", "ingested_at"
            ]
            
            for col in timestamp_cols:
                if col not in df.columns:
                    continue
                
                # Check column dtype
                if df[col].dtype in ['int64', 'float64', 'Int64']:
                    # It's a Unix timestamp (milliseconds)
                    # Convert to datetime using pandas
                    df[col] = pd.to_datetime(df[col], unit='ms', utc=True, errors='coerce')
                    
                    log_event(
                        stage=self.stage_name,
                        block="export_timestamps",
                        level="DEBUG",
                        msg=f"Converted {col} from Unix ms to datetime",
                        extra={"column": col, "records": len(df)},
                    )
                else:
                    # Try ISO format parsing
                    df[col] = pd.to_datetime(df[col], errors='coerce')

            # Export to Parquet
            df.to_parquet(
                file_path,
                index=False,
                engine="pyarrow",
                compression="snappy"
            )
            
            log_event(
                stage=self.stage_name,
                block="export_parquet",
                level="DEBUG",
                msg=f"Exported {len(df)} records to Parquet",
                extra={"file": str(file_path), "records": len(df)},
            )

        except ImportError:
            # Fallback to JSON if pandas not available
            log_event(
                stage=self.stage_name,
                block="export",
                level="WARNING",
                msg="pandas not available, using JSON export",
            )
            json_path = file_path.with_suffix(".json")
            self._export_to_json(records, json_path)
            
        except Exception as e:
            # Fallback on any error
            log_event(
                stage=self.stage_name,
                block="export",
                level="ERROR",
                msg=f"Parquet export failed: {str(e)}, using JSON fallback",
                extra={"error": str(e), "file": str(file_path)},
            )
            json_path = file_path.with_suffix(".json")
            self._export_to_json(records, json_path)

    def _export_to_json(self, records: List[Dict], file_path: Path):
        """Export to JSON format"""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False, default=str)

    def _create_metadata(self, base_dir: Path, grouped: Dict, pipeline_data: Dict):
        """Create metadata in __meta__ directory"""
        meta_dir = base_dir / "__meta__"
        meta_dir.mkdir(parents=True, exist_ok=True)

        # 1. Manifest (JSONL)
        manifest_path = meta_dir / "manifest.jsonl"
        with open(manifest_path, "w") as f:
            for symbol, types_data in grouped.items():
                sanitized = self._sanitize_symbol(symbol)
                for schema_type, records in types_data.items():
                    entry = {
                        "symbol": symbol,
                        "sanitized_symbol": sanitized,
                        "schema_type": schema_type,
                        "record_count": len(records),
                        "exported_at": datetime.utcnow().isoformat(),
                        "file": f"{sanitized}/{schema_type}.parquet",
                    }
                    f.write(json.dumps(entry) + "\n")

        # 2. Pipeline stats
        stats_file = meta_dir / "pipeline_stats.json"
        with open(stats_file, "w") as f:
            json.dump({
                "exported_at": datetime.utcnow().isoformat(),
                "total_symbols": len(grouped),
                "total_records": sum(
                    len(records)
                    for types_data in grouped.values()
                    for records in types_data.values()
                ),
                "pipeline_stats": {
                    "health_check": pipeline_data.get("health_check", {}),
                    "nan_stats": pipeline_data.get("nan_stats", {}),
                    "alignment_stats": pipeline_data.get("alignment_stats", {}),
                    "dedup_stats": pipeline_data.get("dedup_stats", {}),
                    "qa_stats": pipeline_data.get("qa_stats", {}),
                },
            }, f, indent=2, default=str)

        log_event(
            stage=self.stage_name,
            block="metadata",
            level="INFO",
            msg="Metadata created",
            extra={"meta_dir": str(meta_dir)},
        )