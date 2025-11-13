"""
Run script for Complete Data Farm Pipeline (MP-007)
Executes full end-to-end data flow through all stages
"""

from pathlib import Path
import sys
import asyncio

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from marketpilot.data_farm.resilient_data_farm import ResilientDataFarm
from marketpilot.utils.logger import log_event


async def run_complete_pipeline():
    """Execute complete pipeline with all stages"""
    try:
        log_event(
            stage="pipeline",
            block="run_script",
            level="INFO",
            msg="Starting complete pipeline execution (MP-007)",
        )

        # Initialize Data Farm
        farm = ResilientDataFarm(
            config_path="marketpilot/configs/data_farm_config.yaml"
        )

        print("\n" + "=" * 80)
        print("🚀 DATA FARM COMPLETE PIPELINE - MP-007")
        print("=" * 80)
        print("\n✅ Data Farm initialized successfully!")
        print(f"📊 Loaded {len(farm.get_adapters())} adapter(s)")
        print(f"🔧 Loaded {len(farm.stages)} stage(s)")

        # Test symbols
        test_symbols = ["AAPL", "NVDA"]
        print(f"\n📈 Processing symbols: {', '.join(test_symbols)}")
        print("=" * 80)

        # Execute complete pipeline
        print("\n⚙️  Executing pipeline stages:")
        for i, stage in enumerate(farm.stages, 1):
            print(f"   {i}️⃣  {stage.stage_name.replace('_', ' ').title()}")
        print()

        results = await farm.run_complete_pipeline(test_symbols)

        # Print pipeline summary
        print("\n" + "=" * 80)
        print("📋 PIPELINE EXECUTION SUMMARY")
        print("=" * 80)

        # Show stage results
        print("\n🔍 Stage-by-Stage Results:\n")

        # stage_times = []
        for stage in farm.stages:
            stage_name = stage.stage_name
            # Try to extract timing from logs (simplified for demo)
            print(f"   ✅ {stage_name.replace('_', ' ').title():<30} [Completed]")

        # Show key metrics
        print("\n📊 Key Metrics:\n")

        # Health check
        health_check = results.get("health_check", {})
        print(
            f"   🏥 Adapters Healthy: {health_check.get('healthy', 0)}/{health_check.get('total_adapters', 0)}"
        )

        # Data collection
        raw_data = results.get("raw_data", [])
        print(f"   📥 Records Collected: {len(raw_data)}")

        # NaN processing
        nan_stats = results.get("nan_stats", {})
        print(f"   🔧 NaN Values Handled: {nan_stats.get('nan_count', 0)}")

        # Temporal alignment
        alignment_stats = results.get("alignment_stats", {})
        print(f"   ⏰ Timestamps Aligned: {alignment_stats.get('aligned_count', 0)}")

        # Deduplication
        dedup_stats = results.get("dedup_stats", {})
        print(f"   🔄 Duplicates Removed: {dedup_stats.get('duplicates_removed', 0)}")
        print(f"   📝 Unique Records: {dedup_stats.get('unique_records', 0)}")

        # QA
        qa_stats = results.get("qa_stats", {})
        print(f"   ✅ QA Passed: {qa_stats.get('qa_passed', 0)}")
        print(f"   ❌ QA Failed: {qa_stats.get('qa_failed', 0)}")
        print(f"   📊 Pass Rate: {qa_stats.get('pass_rate', '0%')}")

        # Export
        export_stats = results.get("export_stats", {})
        print(f"   💾 Records Exported: {export_stats.get('records_exported', 0)}")

        # Total pipeline time
        pipeline_duration = results.get("pipeline_duration", 0)
        print(f"\n⏱️  Total Pipeline Duration: {pipeline_duration:.3f} seconds")

        # Export files
        exported_files = export_stats.get("exported_files", [])
        if exported_files:
            print("\n📁 Exported Files:")
            for file_path in exported_files:
                print(f"   • {file_path}")

        print("\n" + "=" * 80)

        # Final verdict
        print("\n🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        print("   All stages executed without errors.")

        log_event(
            stage="pipeline",
            block="run_script",
            level="INFO",
            msg="Complete pipeline executed successfully",
            extra={"duration": pipeline_duration},
        )

        print("\n📝 Detailed logs available at:")
        print("   - logs/pipeline/current.jsonl")
        print("   - logs/stages/")
        print("   - logs/adapters/")
        print("   - logs/errors/")
        print()

    except Exception as e:
        log_event(
            stage="pipeline",
            block="run_script",
            level="ERROR",
            msg=f"Pipeline execution failed: {str(e)}",
        )
        print(f"\n❌ PIPELINE EXECUTION FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def main():
    """Main execution function"""
    asyncio.run(run_complete_pipeline())


if __name__ == "__main__":
    main()
