"""
Main execution script for ResilientDataFarm with start/end support for price adapters
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from marketpilot.data_farm.resilient_data_farm import ResilientDataFarm


async def main():
    """Run complete data farm pipeline with optional start/end for price adapters"""

    # Load environment variables
    load_dotenv()

    print("=" * 80)
    print("🚀 MarketPilot - Resilient Data Farm")
    print("=" * 80)

    try:
        # Initialize Data Farm
        print("\n📦 Initializing Data Farm...")
        farm = ResilientDataFarm()

        # Get target symbols from config
        config = farm.get_config()
        symbols = config.get("target_symbols", ["BINANCE:BTCUSDT.P"])

        print("✅ Data Farm initialized")
        print(f"   Symbols: {symbols}")
        print(f"   Adapters: {len(farm.get_adapters())}")

        # Step 1: Run smoke test
        print("\n" + "=" * 80)
        print("🧪 Step 1: Running Smoke Test")
        print("=" * 80)

        smoke_results = await farm.run_smoke_test(symbols)

        print("\n📊 Smoke Test Results:")
        print(f"   Total tests: {smoke_results['total_tests']}")
        print(f"   ✅ Passed: {smoke_results['passed']}")
        print(f"   ❌ Failed: {smoke_results['failed']}")

        # Show details
        for detail in smoke_results["details"]:
            status_icon = detail["status"]
            print(
                f"   {status_icon} {detail['adapter_id']} - {detail['symbol']}", end=""
            )
            if "record_count" in detail:
                print(f" ({detail['record_count']} records)")
            elif "error" in detail:
                print(f" - Error: {detail['error']}")
            else:
                print()

        # Step 2: Run complete pipeline if smoke test passed
        if smoke_results["failed"] == 0:
            print("\n" + "=" * 80)
            print("🏭 Step 2: Running Complete Pipeline")
            print("=" * 80)

            # FIX: Iterate over adapter objects, not keys
            # Option 1: Use .values() to get adapter objects
            for adapter in farm.get_adapters().values():
                if adapter.schema_type == "price":
                    end = datetime.utcnow()
                    start = end - timedelta(minutes=10)  # Example: last 10 minutes
                    print(
                        f"\n📌 Fetching price data for {adapter.adapter_id} (last 10 min)"
                    )
                    result = await adapter.execute_ingest(
                        symbols[0], start=start, end=end
                    )
                    print(f"Result: {result}")

            # Run pipeline for other data types if needed
            pipeline_results = await farm.run_complete_pipeline(
                symbols=symbols, data_types=["price"]  # Expand as needed
            )

            print("\n✅ Pipeline Completed Successfully!")
            print(f"   Duration: {pipeline_results.get('pipeline_duration', 0):.2f}s")
            print(
                f"   Records fetched: {pipeline_results['fetch_summary']['total_records']}"
            )
            print(
                f"   Successful fetches: {pipeline_results['fetch_summary']['successful_fetches']}"
            )
            print(
                f"   Failed fetches: {pipeline_results['fetch_summary']['failed_fetches']}"
            )

            # Show stage results
            if "nan_stats" in pipeline_results:
                print("\n📊 Pipeline Stages:")
                print(
                    f"   NaN Processing: {pipeline_results['nan_stats'].get('nan_count', 0)} NaNs fixed"
                )

            if "alignment_stats" in pipeline_results:
                print(
                    f"   Temporal Alignment: {pipeline_results['alignment_stats'].get('aligned_count', 0)} records aligned"
                )

            if "dedup_stats" in pipeline_results:
                print(
                    f"   Deduplication: {pipeline_results['dedup_stats'].get('duplicates_removed', 0)} duplicates removed"
                )

            if "qa_stats" in pipeline_results:
                qa = pipeline_results["qa_stats"]
                print(
                    f"   Quality Assurance: {qa.get('qa_passed', 0)}/{qa.get('total_records', 0)} passed ({qa.get('pass_rate', '0%')})"
                )

            if "export_stats" in pipeline_results:
                export = pipeline_results["export_stats"]
                print("\n📁 Export Results:")
                print(f"   Files exported: {len(export.get('exported_files', []))}")
                print(f"   Records exported: {export.get('records_exported', 0)}")
                print(
                    f"   Symbols processed: {', '.join(export.get('symbols_processed', []))}"
                )

            # Validation results
            validation = pipeline_results.get("validation_report", {})
            if validation.get("validation_passed"):
                print("\n✅ Schema Validation: PASSED")
            else:
                print("\n❌ Schema Validation: FAILED")
                if validation.get("errors"):
                    print("   Errors:")
                    for error in validation["errors"]:
                        print(f"   - {error}")

        else:
            print("\n⚠️  Skipping pipeline execution due to smoke test failures")
            print("   Please fix the errors above and try again")

    except Exception as e:
        print(f"\n❌ Fatal Error: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 80)
    print("✅ Data Farm execution complete")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
