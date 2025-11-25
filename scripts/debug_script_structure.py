"""
Debug script to check data structure at each stage
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from marketpilot.data_farm.resilient_data_farm import ResilientDataFarm


async def main():
    """Debug data structure"""

    load_dotenv()

    print("=" * 80)
    print("🔍 DEBUG: Data Structure Check")
    print("=" * 80)

    try:
        farm = ResilientDataFarm()

        symbols = ["bitcoin"]

        print(f"\n📊 Fetching data for: {symbols}")

        # Fetch data
        fetch_results = await farm.fetch_data_for_symbols(symbols, ["news"])

        # Check structure
        print("\n" + "=" * 80)
        print("📦 RAW DATA STRUCTURE")
        print("=" * 80)

        raw_data = fetch_results.get("raw_data", {})

        for data_type, symbols_data in raw_data.items():
            print(f"\n{data_type.upper()}:")
            for symbol, data in symbols_data.items():
                print(f"  Symbol: {symbol}")
                print(f"  Type: {type(data).__name__}")

                if isinstance(data, dict):
                    print(f"  Keys: {list(data.keys())}")
                    if "data" in data:
                        articles = data["data"]
                        print(
                            f"  Articles count: {len(articles) if isinstance(articles, list) else 'Not a list'}"
                        )
                        if isinstance(articles, list) and articles:
                            print("\n  📄 Sample Article:")
                            sample = articles[0]
                            for key, value in list(sample.items())[:5]:
                                print(f"    {key}: {str(value)[:50]}")
                elif isinstance(data, list):
                    print(f"  Count: {len(data)}")
                    if data:
                        print(
                            f"  First item keys: {list(data[0].keys()) if isinstance(data[0], dict) else 'Not dict'}"
                        )

        print("\n" + "=" * 80)

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())