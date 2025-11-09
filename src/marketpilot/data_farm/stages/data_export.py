"""
Data Export Stage - Export processed data to output directory
"""

from typing import Dict, Any
import json
from pathlib import Path
from datetime import datetime
from marketpilot.data_farm.stages.base_stage import BaseStage
from marketpilot.utils.logger import log_event


class DataExportStage(BaseStage):
    """Export validated data to output directory"""

    def __init__(self):
        super().__init__("data_export")

    async def _process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Export data to output directory"""
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
        output_dir = Path(config.get("output", {}).get("base_dir", "data/output"))
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate export filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_file = output_dir / f"data_farm_export_{timestamp}.json"

        # Prepare export data
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "total_records": len(validated_data),
            "pipeline_stats": {
                "health_check": data.get("health_check", {}),
                "nan_stats": data.get("nan_stats", {}),
                "alignment_stats": data.get("alignment_stats", {}),
                "dedup_stats": data.get("dedup_stats", {}),
                "qa_stats": data.get("qa_stats", {}),
            },
            "data": validated_data,
        }

        # Write to file
        try:
            with open(export_file, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            log_event(
                stage=self.stage_name,
                block="data_export",
                level="INFO",
                msg="Data exported successfully",
                extra={
                    "file": str(export_file),
                    "records_exported": len(validated_data),
                },
            )

            data["export_stats"] = {
                "exported_files": [str(export_file)],
                "records_exported": len(validated_data),
            }

        except Exception as e:
            log_event(
                stage=self.stage_name,
                block="data_export",
                level="ERROR",
                msg=f"Failed to export data: {str(e)}",
            )
            raise

        return data
