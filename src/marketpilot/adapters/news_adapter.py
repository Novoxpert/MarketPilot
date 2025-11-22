from typing import List, Dict, Any
from datetime import datetime, timedelta
from marketpilot.adapters.base_adapter import BaseAdapter


class ResilientNewsAdapter(BaseAdapter):
    """News data adapter"""

    async def _execute_ingest_internal(
        self, symbol: str, start: datetime = None, end: datetime = None
    ) -> Dict[str, Any]:
        """Ingest news data for a symbol"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=1)

            # Mock news data with timestamp field
            mock_news = [
                {
                    "title": f"{symbol} Stock Analysis",
                    "url": "https://example.com/news1",
                    "published_at": datetime.utcnow().isoformat(),
                    "sentiment": "positive",
                },
                {
                    "title": f"{symbol} Quarterly Earnings",
                    "url": "https://example.com/news2",
                    "published_at": (
                        datetime.utcnow() - timedelta(hours=3)
                    ).isoformat(),
                    "sentiment": "neutral",
                },
            ]

            result_data = {
                "symbol": symbol,
                "timestamp": datetime.utcnow().isoformat(),
                "startdate": start_date.isoformat(),
                "enddate": end_date.isoformat(),
                "data": mock_news,
            }

            print("eeeeeeeee")
            self.validate_schema(result_data)
            self.log_success(symbol, record_count=len(mock_news))

            return {
                "success": True,
                "data": result_data,
                "vendor": self.vendor,
                "ingested_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            self.log_error(symbol, str(e))
            return {"success": False, "error": str(e), "vendor": self.vendor}


class ResilientFundamentalAdapter(BaseAdapter):
    """Fundamental data adapter using FMP"""

    async def _execute_ingest_internal(self, symbol: str) -> Dict[str, Any]:
        """Ingest fundamental data for a symbol"""
        try:
            end_date = datetime.utcnow()
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
                "timestamp": datetime.utcnow().isoformat(),
                "startdate": start_date.isoformat(),
                "enddate": end_date.isoformat(),
                "data": mock_fundamentals,
            }

            print("wwwwwwwwww")
            self.validate_schema(result_data)
            self.log_success(symbol, record_count=1)

            return {
                "success": True,
                "data": result_data,
                "vendor": self.vendor,
                "ingested_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            self.log_error(symbol, str(e))
            return {"success": False, "error": str(e), "vendor": self.vendor}


"""
Alternative: Update QA Stage to be more flexible with timestamps
This approach allows adapters to use different timestamp field names
"""


class FlexibleQualityAssuranceStage:
    """QA stage that accepts multiple timestamp field variations"""

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

            # Check 1: Symbol exists
            if "symbol" not in record or not record.get("symbol"):
                qa_issues.append("Missing symbol")

            # Check 2: Adapter ID exists
            if "adapter_id" not in record or not record.get("adapter_id"):
                qa_issues.append("Missing adapter_id")

            # Check 3: Data payload exists
            if not record_data or len(record_data) == 0:
                qa_issues.append("Empty data payload")

            #  Check 4: Flexible timestamp validation
            # Accept any of these timestamp fields
            timestamp_fields = [
                "timestamp",
                "date",
                "datetime",
                "time",
                "published_at",
                "created_at",
                "updated_at",
            ]

            has_timestamp = False
            # timestamp_value = None

            for field in timestamp_fields:
                if field in record_data and record_data[field]:
                    has_timestamp = True
                    # timestamp_value = record_data[field]
                    break

            # Also check if timestamp exists in nested data
            if not has_timestamp and "data" in record_data:
                nested_data = record_data["data"]
                if isinstance(nested_data, dict):
                    for field in timestamp_fields:
                        if field in nested_data and nested_data[field]:
                            has_timestamp = True
                            # timestamp_value = nested_data[field]
                            break

            if not has_timestamp:
                qa_issues.append("Missing timestamp field")

            # Check 5: Price data validation
            if "open" in record_data or "close" in record_data:
                try:
                    for price_field in ["open", "high", "low", "close"]:
                        if price_field in record_data:
                            price_value = record_data[price_field]
                            if price_value is not None:
                                float(price_value)
                except (ValueError, TypeError) as e:
                    qa_issues.append(f"Invalid numeric value: {str(e)}")

            # Check 6: Volume validation
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
            else:
                qa_passed += 1
                validated_records.append(record)

        pass_rate = (
            f"{(qa_passed / len(unique_data) * 100):.1f}%" if unique_data else "0%"
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
