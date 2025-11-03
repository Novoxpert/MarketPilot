"""
Base Adapter for Data Farm
All adapters inherit from this class
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from data_farm.utils.logger import log_event


class BaseAdapter(ABC):
    """Base class for all data adapters"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize adapter with configuration
        
        Args:
            config: Adapter configuration containing:
                - vendor: Vendor name (e.g., 'yfinance', 'alphavantage')
                - id: Unique adapter ID
                - cadence: Update frequency (e.g., '1min', 'daily')
        """
        self.vendor = config.get("vendor", "unknown")
        self.adapter_id = config.get("id", "unknown")
        self.cadence = config.get("cadence", "daily")
        
        log_event(
            stage="ingestion",
            block=f"{self.vendor}_adapter",
            level="INFO",
            msg=f"Adapter initialized: {self.adapter_id}",
            extra={"cadence": self.cadence}
        )
    
    @abstractmethod
    async def execute_ingest(self, symbol: str) -> Dict[str, Any]:
        """
        Execute data ingestion for a symbol
        
        Args:
            symbol: Asset symbol (e.g., 'AAPL', 'TSLA')
            
        Returns:
            Dictionary containing ingested data
        """
        pass
    
    def log_success(self, symbol: str, record_count: int):
        """Log successful ingestion"""
        log_event(
            stage="ingestion",
            block=f"{self.vendor}_adapter",
            level="INFO",
            msg=f"Successfully ingested data for {symbol}",
            extra={
                "symbol": symbol,
                "records": record_count,
                "adapter_id": self.adapter_id
            }
        )
    
    def log_error(self, symbol: str, error: str):
        """Log ingestion error"""
        log_event(
            stage="ingestion",
            block=f"{self.vendor}_adapter",
            level="ERROR",
            msg=f"Failed to ingest data for {symbol}",
            extra={
                "symbol": symbol,
                "error": error,
                "adapter_id": self.adapter_id
            }
        )