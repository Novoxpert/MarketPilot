"""
Main execution script for ResilientDataFarm with start/end support for price and news adapters
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
    """Run complete data farm pipeline with optional start/end for adapters"""

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
        symbols = config.get("target_symbols", ["bitcoin", "ethereum"])

        print("✅ Data Farm initialized")
        print(f"   Symbols: {symbols}")
        print(f"   Adapters: {len(farm.get_adapters())}")

        # Display loaded adapters by type
        print("\n📋 Loaded Adapters:")
        for adapter_type in ["price", "news", "fundamental"]:
            adapters_of_type = farm.get_adapters_by_type(adapter_type)
            if adapters_of_type:
                print(f"   {adapter_type.upper()}:")
                for adapter in adapters_of_type:
                    print(f"      • {adapter.adapter_id} ({adapter.vendor})")

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

            # Define time ranges for different data types
            end_time = datetime.utcnow()

            # Price: Last 10 minutes
            price_start = end_time - timedelta(minutes=10)

            # News: Last 24 hours
            news_start = end_time - timedelta(days=1)

            print("\n📅 Time Ranges:")
            print(
                f"   Price data: {price_start.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}"
            )
            print(
                f"   News data: {news_start.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}"
            )

            # Determine which data types to fetch based on available adapters
            data_types_to_fetch = []
            if farm.get_adapters_by_type("price"):
                data_types_to_fetch.append("price")
            if farm.get_adapters_by_type("news"):
                data_types_to_fetch.append("news")
            if farm.get_adapters_by_type("fundamental"):
                data_types_to_fetch.append("fundamental")

            print(f"\n📊 Data types to process: {', '.join(data_types_to_fetch)}")

            # Run complete pipeline
            pipeline_results = await farm.run_complete_pipeline(
                symbols=symbols, data_types=data_types_to_fetch
            )

            print("\n✅ Pipeline Completed Successfully!")
            print(f"   Duration: {pipeline_results.get('pipeline_duration', 0):.2f}s")

            # Fetch summary
            fetch_summary = pipeline_results.get("fetch_summary", {})
            print(f"   Records fetched: {fetch_summary.get('total_records', 0)}")
            print(
                f"   Successful fetches: {fetch_summary.get('successful_fetches', 0)}"
            )
            print(f"   Failed fetches: {fetch_summary.get('failed_fetches', 0)}")

            # Show fetch errors if any
            fetch_errors = pipeline_results.get("fetch_errors", [])
            if fetch_errors:
                print("\n⚠️  Fetch Errors:")
                for error in fetch_errors:
                    print(
                        f"   • {error['symbol']} ({error['data_type']}): {error['error']}"
                    )

            # Show stage results
            print("\n📊 Pipeline Stages:")

            if "nan_stats" in pipeline_results:
                print(
                    f"   NaN Processing: {pipeline_results['nan_stats'].get('nan_count', 0)} NaNs fixed"
                )

            if "alignment_stats" in pipeline_results:
                alignment = pipeline_results["alignment_stats"]
                print(
                    f"   Temporal Alignment: {alignment.get('aligned_count', 0)}/{alignment.get('total_records', 0)} records aligned ({alignment.get('alignment_rate', '0%')})"
                )

            if "dedup_stats" in pipeline_results:
                dedup = pipeline_results["dedup_stats"]
                print(
                    f"   Deduplication: {dedup.get('duplicates_removed', 0)} duplicates removed, {dedup.get('unique_records', 0)} unique records kept ({dedup.get('deduplication_rate', '0%')})"
                )

            if "qa_stats" in pipeline_results:
                qa = pipeline_results["qa_stats"]
                threshold_icon = "✅" if qa.get("threshold_met", False) else "⚠️"
                print(
                    f"   Quality Assurance: {threshold_icon} {qa.get('qa_passed', 0)}/{qa.get('total_records', 0)} passed ({qa.get('pass_rate', '0%')})"
                )

                # Show QA issues if any
                qa_issues = qa.get("issues", [])
                if qa_issues:
                    print(f"\n   ⚠️  QA Issues Found ({len(qa_issues)}):")
                    for issue in qa_issues[:5]:  # Show first 5
                        print(
                            f"      • {issue['symbol']} ({issue['schema_type']}): {', '.join(issue['issues'])}"
                        )
                    if len(qa_issues) > 5:
                        print(f"      ... and {len(qa_issues) - 5} more")

            if "export_stats" in pipeline_results:
                export = pipeline_results["export_stats"]
                print("\n📁 Export Results:")
                print(f"   Files exported: {len(export.get('exported_files', []))}")
                print(f"   Records exported: {export.get('records_exported', 0)}")
                print(f"   Output directory: {export.get('output_directory', 'N/A')}")
                print(
                    f"   Symbols processed: {', '.join(export.get('symbols_processed', []))}"
                )

                # Show exported files by symbol
                exported_files = export.get("exported_files", [])
                if exported_files:
                    print("\n   Exported files:")
                    for file_path in exported_files[:10]:  # Show first 10
                        print(f"      • {file_path}")
                    if len(exported_files) > 10:
                        print(f"      ... and {len(exported_files) - 10} more")

            # Validation results
            validation = pipeline_results.get("validation_report", {})
            print("\n🔍 Schema Validation:")
            if validation.get("validation_passed"):
                print("   ✅ PASSED")
                stages_validated = validation.get("stages_validated", [])
                if stages_validated:
                    stage_strs = [str(stage) for stage in stages_validated]
                    print(f"   Validated stages: {', '.join(stage_strs)}")
            else:
                print("   ❌ FAILED")
                if validation.get("errors"):
                    print("   Errors:")
                    for error in validation["errors"]:
                        print(f"      • {error}")

            # Show warnings if any
            warnings = validation.get("warnings", [])
            if warnings:
                print("   ⚠️  Warnings:")
                for warning in warnings:
                    print(f"      • {warning}")

            # Final summary
            print("\n" + "=" * 80)
            print("📈 SUMMARY")
            print("=" * 80)
            print(f"   Total symbols processed: {len(symbols)}")
            print(f"   Total data types: {len(data_types_to_fetch)}")
            print(f"   Total records exported: {export.get('records_exported', 0)}")
            print(
                f"   Pipeline duration: {pipeline_results.get('pipeline_duration', 0):.2f}s"
            )
            print(
                f"   Quality threshold met: {'✅ Yes' if qa.get('threshold_met', False) else '⚠️  No'}"
            )

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
    print("\n📝 Logs available at:")
    print("   • logs/pipeline/current.jsonl")
    print("   • logs/stages/*.jsonl")
    print("   • logs/adapters/*.jsonl")
    print("   • logs/errors/current.jsonl")
    print()


if __name__ == "__main__":
    asyncio.run(main())
