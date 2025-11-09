"""
Resilient Fundamental Adapter using Financial Modeling Prep (FMP)
Inherits schema validation from BaseAdapter
FIXED: Added timestamp field to result_data
"""

from typing import Dict, Any
from datetime import datetime, timedelta
from marketpilot.adapters.base_adapter import BaseAdapter


class ResilientFundamentalAdapter(BaseAdapter):
    """Fundamental data adapter using FMP"""

    async def execute_ingest(self, symbol: str) -> Dict[str, Any]:
        """
        Ingest fundamental data for a symbol

        Args:
            symbol: Stock symbol (e.g., 'AAPL')

        Returns:
            Dictionary with fundamental data
        """
        try:
            # TODO: Replace with actual FMP API call
            # For now, return mock data

            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)

            # Mock fundamental data
            mock_fundamentals = {
                "income_statement": {
                    "revenue": 394328000000,
                    "net_income": 99803000000,
                    "eps": 6.15,
                },
                "balance_sheet": {
                    "total_assets": 352755000000,
                    "total_liabilities": 302083000000,
                    "stockholders_equity": 50672000000,
                },
                "cash_flow": {
                    "operating_cash_flow": 122151000000,
                    "capital_expenditure": -10959000000,
                    "free_cash_flow": 111192000000,
                },
                "ratios": {"pe_ratio": 28.5, "debt_to_equity": 5.96, "roe": 0.196},
            }

            result_data = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),  # ✅ ADDED THIS LINE
                "startdate": start_date.isoformat(),
                "enddate": end_date.isoformat(),
                "data": mock_fundamentals,
            }

            # ✅ Validate against schema BEFORE returning
            self.validate_schema(result_data)

            self.log_success(symbol, record_count=1)

            return {
                "success": True,
                "data": result_data,
                "vendor": self.vendor,
                "ingested_at": datetime.now().isoformat(),
            }

        except Exception as e:
            self.log_error(symbol, str(e))
            return {"success": False, "error": str(e), "vendor": self.vendor}


# Example usage
if __name__ == "__main__":
    import asyncio

    config = {
        "vendor": "fmp",
        "id": "fundamental_fmp_001",
        "cadence": "daily",
        "schema_type": "fundamental",
    }

    adapter = ResilientFundamentalAdapter(config)
    result = asyncio.run(adapter.execute_ingest("AAPL"))
    print(result)
