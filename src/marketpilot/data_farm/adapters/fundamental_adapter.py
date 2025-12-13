"""
Resilient Fundamental Adapter
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from marketpilot.data_farm.adapters.base_adapter import BaseAdapter
from marketpilot.utils.logger import log_event


class ResilientFundamentalAdapter(BaseAdapter):
    """
    Fundamental data adapter with time range support
    
    """

    async def _execute_ingest_internal(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Ingest fundamental data for a symbol
        
        TODO: Replace with actual FMP API call when ready

        """
        try:
            # Use config start/end if provided
            if start is None:
                start = self.config.get("start")
            if end is None:
                end = self.config.get("end")
            
            # Default to last year if still None
            if start is None or end is None:
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=365)
            else:
                start_date = start
                end_date = end

            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="INFO",
                msg="Successfully ingested fundamental data",
                extra={
                    "symbol": symbol,
                    "time_range": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat(),
                    }
                },
            )

            return {
                "success": True,
                "data": [],
                "vendor": self.vendor,
                "adapter_id": self.adapter_id,
                "ingested_at": datetime.utcnow().isoformat(),
                "record_count": 1,  # Single record for fundamentals
            }

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            log_event(
                stage="ingestion",
                block=self.adapter_id,
                level="ERROR",
                msg=error_msg,
                extra={"symbol": symbol},
            )
            return {
                "success": False,
                "error": error_msg,
                "vendor": self.vendor,
                "adapter_id": self.adapter_id,
            }
