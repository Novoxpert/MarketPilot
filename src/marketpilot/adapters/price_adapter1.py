# """
# Resilient Price Adapter using YFinance
# Connects to Yahoo Finance API for real-time price data
# """

# from typing import Dict, Any, Optional
# from datetime import datetime, timedelta
# import yfinance as yf
# from marketpilot.adapters.base_adapter import BaseAdapter
# from marketpilot.utils.logger import log_event


# class ResilientPriceAdapter(BaseAdapter):
#     """Price data adapter using YFinance"""

#     def __init__(self, config: Dict[str, Any]):
#         """
#         Initialize Price Adapter
        
#         Args:
#             config: Configuration dictionary containing:
#                 - vendor: 'yfinance'
#                 - id: Unique adapter ID
#                 - cadence: Data frequency (1m, 5m, 1h, 1d, etc.)
#                 - period: Time period (1d, 5d, 1mo, etc.)
#         """
#         super().__init__(config)
        
#         # Parse cadence/interval from config
#         self.interval = config.get("cadence", "1m")  # مثلاً: 1m, 5m, 1h, 1d
#         self.period = config.get("period", "1d")     # مثلاً: 1d, 5d, 1mo
        
#         log_event(
#             stage="adapter_init",
#             block="price_adapter",
#             level="INFO",
#             msg="Price adapter initialized",
#             extra={
#                 "adapter_id": self.adapter_id,
#                 "interval": self.interval,
#                 "period": self.period
#             }
#         )

#     async def execute_ingest(self, symbol: str) -> Dict[str, Any]:
#         """
#         Ingest price data for a symbol from Yahoo Finance

#         Args:
#             symbol: Stock symbol (e.g., 'AAPL', 'GOOGL')

#         Returns:
#             Dictionary with price data or error
#         """
#         try:
#             log_event(
#                 stage="data_ingestion",
#                 block="price_adapter",
#                 level="INFO",
#                 msg=f"Fetching price data for {symbol}",
#                 extra={
#                     "symbol": symbol,
#                     "interval": self.interval,
#                     "period": self.period
#                 }
#             )

#             # ✅ دریافت داده از Yahoo Finance
#             ticker = yf.Ticker(symbol)
            
#             # دریافت historical data
#             hist = ticker.history(
#                 period=self.period,
#                 interval=self.interval
#             )
            
#             # بررسی خالی بودن داده
#             if hist.empty:
#                 error_msg = f"No data available for {symbol}"
#                 self.log_error(symbol, error_msg)
#                 return {
#                     "success": False,
#                     "error": error_msg,
#                     "vendor": self.vendor
#                 }
            
#             # ✅ آخرین رکورد (جدیدترین قیمت)
#             latest = hist.iloc[-1]
#             latest_timestamp = hist.index[-1]
            
#             # ✅ تبدیل به فرمت استاندارد
#             price_data = {
#                 "symbol": symbol,
#                 "timestamp": latest_timestamp.isoformat(),
#                 "open": float(latest["Open"]),
#                 "high": float(latest["High"]),
#                 "low": float(latest["Low"]),
#                 "close": float(latest["Close"]),
#                 "volume": int(latest["Volume"]),
#                 "adjusted_close": float(latest["Close"])  # yfinance automatically adjusts
#             }
            
#             # ✅ Validate against schema
#             self.validate_schema(price_data)
            
#             # ✅ Log success
#             self.log_success(symbol, record_count=1)
            
#             return {
#                 "success": True,
#                 "data": price_data,
#                 "vendor": self.vendor,
#                 "adapter_id": self.adapter_id,
#                 "ingested_at": datetime.now().isoformat(),
#                 "total_records": len(hist),  # تعداد کل رکوردها
#             }

#         except Exception as e:
#             self.log_error(symbol, str(e))
#             return {
#                 "success": False,
#                 "error": str(e),
#                 "vendor": self.vendor,
#                 "adapter_id": self.adapter_id
#             }

#     async def fetch_historical_data(
#         self, 
#         symbol: str, 
#         start_date: Optional[datetime] = None,
#         end_date: Optional[datetime] = None
#     ) -> Dict[str, Any]:
#         """
#         دریافت داده‌های تاریخی با بازه زمانی مشخص
        
#         Args:
#             symbol: نماد سهم
#             start_date: تاریخ شروع (اختیاری)
#             end_date: تاریخ پایان (اختیاری)
            
#         Returns:
#             لیست تمام رکوردهای تاریخی
#         """
#         try:
#             # تنظیم تاریخ‌های پیش‌فرض
#             if end_date is None:
#                 end_date = datetime.now()
#             if start_date is None:
#                 start_date = end_date - timedelta(days=30)  # 30 روز گذشته
            
#             log_event(
#                 stage="data_ingestion",
#                 block="price_adapter",
#                 level="INFO",
#                 msg=f"Fetching historical data for {symbol}",
#                 extra={
#                     "symbol": symbol,
#                     "start_date": start_date.isoformat(),
#                     "end_date": end_date.isoformat(),
#                     "interval": self.interval
#                 }
#             )
            
#             # دریافت داده از Yahoo Finance
#             ticker = yf.Ticker(symbol)
#             hist = ticker.history(
#                 start=start_date,
#                 end=end_date,
#                 interval=self.interval
#             )
            
#             if hist.empty:
#                 error_msg = f"No historical data for {symbol}"
#                 self.log_error(symbol, error_msg)
#                 return {
#                     "success": False,
#                     "error": error_msg,
#                     "vendor": self.vendor
#                 }
            
#             # تبدیل همه رکوردها
#             all_records = []
#             for timestamp, row in hist.iterrows():
#                 record = {
#                     "symbol": symbol,
#                     "timestamp": timestamp.isoformat(),
#                     "open": float(row["Open"]),
#                     "high": float(row["High"]),
#                     "low": float(row["Low"]),
#                     "close": float(row["Close"]),
#                     "volume": int(row["Volume"]),
#                     "adjusted_close": float(row["Close"])
#                 }
#                 all_records.append(record)
            
#             self.log_success(symbol, record_count=len(all_records))
            
#             return {
#                 "success": True,
#                 "data": all_records,
#                 "vendor": self.vendor,
#                 "adapter_id": self.adapter_id,
#                 "ingested_at": datetime.now().isoformat(),
#                 "total_records": len(all_records),
#                 "date_range": {
#                     "start": start_date.isoformat(),
#                     "end": end_date.isoformat()
#                 }
#             }
            
#         except Exception as e:
#             self.log_error(symbol, str(e))
#             return {
#                 "success": False,
#                 "error": str(e),
#                 "vendor": self.vendor,
#                 "adapter_id": self.adapter_id
#             }

#     async def health_check(self) -> bool:
#         """
#         بررسی سلامت اتصال به Yahoo Finance
        
#         Returns:
#             True اگر اتصال سالم باشد
#         """
#         try:
#             log_event(
#                 stage="health_check",
#                 block="price_adapter",
#                 level="INFO",
#                 msg="Running health check",
#                 extra={"adapter_id": self.adapter_id}
#             )
            
#             # تست با سهم معروف
#             ticker = yf.Ticker("AAPL")
#             info = ticker.info
            
#             # بررسی اینکه داده دریافت شده است
#             is_healthy = info is not None and len(info) > 0
            
#             log_event(
#                 stage="health_check",
#                 block="price_adapter",
#                 level="INFO" if is_healthy else "ERROR",
#                 msg="Health check completed",
#                 extra={
#                     "adapter_id": self.adapter_id,
#                     "status": "healthy" if is_healthy else "unhealthy"
#                 }
#             )
            
#             return is_healthy
            
#         except Exception as e:
#             log_event(
#                 stage="health_check",
#                 block="price_adapter",
#                 level="ERROR",
#                 msg=f"Health check failed: {str(e)}",
#                 extra={"adapter_id": self.adapter_id}
#             )
#             return False

#     def get_available_intervals(self) -> list:
#         """
#         لیست interval های در دسترس Yahoo Finance
        
#         Returns:
#             لیست فواصل زمانی معتبر
#         """
#         return ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"]

#     def get_available_periods(self) -> list:
#         """
#         لیست period های در دسترس Yahoo Finance
        
#         Returns:
#             لیست دوره‌های زمانی معتبر
#         """
#         return ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]


# # ✅ Example usage & testing
# if __name__ == "__main__":
#     import asyncio

#     async def test_adapter():
#         """تست کامل adapter"""
        
#         # پیکربندی
#         config = {
#             "vendor": "yfinance",
#             "id": "price_yfinance_001",
#             "cadence": "1m",  # داده هر دقیقه
#             "period": "1d"    # برای 1 روز گذشته
#         }

#         # ساخت adapter
#         adapter = ResilientPriceAdapter(config)
        
#         print("\n" + "="*60)
#         print("🧪 Testing Yahoo Finance Price Adapter")
#         print("="*60)
        
#         # تست 1: Health Check
#         print("\n1️⃣ Health Check...")
#         is_healthy = await adapter.health_check()
#         print(f"   Status: {'✅ Healthy' if is_healthy else '❌ Unhealthy'}")
        
#         # تست 2: دریافت آخرین قیمت
#         print("\n2️⃣ Fetching latest price for AAPL...")
#         result = await adapter.execute_ingest("AAPL")
        
#         if result["success"]:
#             print("   ✅ Success!")
#             print(f"   Symbol: {result['data']['symbol']}")
#             print(f"   Timestamp: {result['data']['timestamp']}")
#             print(f"   Open: ${result['data']['open']:.2f}")
#             print(f"   High: ${result['data']['high']:.2f}")
#             print(f"   Low: ${result['data']['low']:.2f}")
#             print(f"   Close: ${result['data']['close']:.2f}")
#             print(f"   Volume: {result['data']['volume']:,}")
#         else:
#             print(f"   ❌ Failed: {result['error']}")
        
#         # تست 3: دریافت داده تاریخی
#         print("\n3️⃣ Fetching historical data (last 7 days)...")
#         end = datetime.now()
#         start = end - timedelta(days=7)
        
#         hist_result = await adapter.fetch_historical_data("AAPL", start, end)
        
#         if hist_result["success"]:
#             print(f"   ✅ Success!")
#             print(f"   Total records: {hist_result['total_records']}")
#             print(f"   Date range: {hist_result['date_range']['start']} to {hist_result['date_range']['end']}")
#             if hist_result['total_records'] > 0:
#                 first_record = hist_result['data'][0]
#                 print(f"   First record: {first_record['timestamp']} - Close: ${first_record['close']:.2f}")
#         else:
#             print(f"   ❌ Failed: {hist_result['error']}")
        
#         print("\n" + "="*60)

#     # اجرای تست
#     asyncio.run(test_adapter())