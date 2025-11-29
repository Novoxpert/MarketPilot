"""
Simple Complete Pipeline Runner
Quick execution with default settings
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
    """Execute complete pipeline with default configuration"""
    
    print("\n" + "=" * 80)
    print("🏭 DATA FARM - COMPLETE PIPELINE")
    print("=" * 80)
    
    try:
        log_event(
            stage="pipeline",
            block="run_script",
            level="INFO",
            msg="Starting pipeline execution",
        )

        # ========================================
        # Step 1: Initialize
        # ========================================
        print("\n🔧 Step 1/3: Initializing Data Farm...")
        
        farm = ResilientDataFarm(
            config_path="src/marketpilot/configs/data/data_farm_config.yml"
        )

        print(f"   ✅ Data Farm initialized")
        print(f"   Adapters: {len(farm.get_adapters())}")
        print(f"   Stages: {len(farm.stages)}")
        
        # Show adapters
        print(f"\n   Loaded Adapters:")
        for adapter in farm.get_adapters():
            print(f"      • {adapter.adapter_id} ({adapter.schema_type} - {adapter.vendor})")
        
        # Show stages
        print(f"\n   Pipeline Stages:")
        for i, stage in enumerate(farm.stages, 1):
            stage_name = stage.stage_name.replace('_', ' ').title()
            print(f"      {i}. {stage_name}")

        # ========================================
        # Step 2: Configure Symbols
        # ========================================
        print(f"\n🎯 Step 2/3: Configuring Symbols...")
        
        # Get symbols from config or use defaults
        test_symbols = farm.get_config().get("target_symbols", [
            "BINANCE:BTCUSDT.P",
            "BINANCE:ETHUSDT.P"
        ])
        
        print(f"   Symbols: {', '.join(test_symbols)}")

        # ========================================
        # Step 3: Execute Pipeline
        # ========================================
        print(f"\n🚀 Step 3/3: Executing Pipeline...")
        print("="*80 + "\n")
        
        results = await farm.run_complete_pipeline(test_symbols)

        # ========================================
        # Results Summary
        # ========================================
        print("\n" + "="*80)
        print("📊 PIPELINE RESULTS")
        print("="*80)

        if not results.get("pipeline_success"):
            print("\n❌ PIPELINE FAILED")
            print(f"Error: {results.get('error', 'Unknown')}")
            return

        # Health Check
        health_check = results.get("health_check", {})
        if health_check:
            status = health_check.get('overall_status', 'unknown')
            apis_healthy = health_check.get('apis_healthy', 0)
            apis_checked = health_check.get('apis_checked', 0)
            
            status_icon = "✅" if status == "healthy" else "⚠️" if status == "degraded" else "❌"
            print(f"\n{status_icon} Health Check: {status.upper()}")
            print(f"   APIs: {apis_healthy}/{apis_checked} healthy")

        # Data Collection
        collection = results.get("collection_summary", {})
        if collection:
            total_records = collection.get('total_records', 0)
            successful = collection.get('successful', 0)
            failed = collection.get('failed', 0)
            
            print(f"\n📥 Data Collection:")
            print(f"   Records: {total_records}")
            print(f"   Successful: {successful}")
            print(f"   Failed: {failed}")

        # NaN Processing
        nan_stats = results.get("nan_stats", {})
        if nan_stats:
            nan_count = nan_stats.get('nan_count', 0)
            print(f"\n🧹 NaN Processing:")
            print(f"   Values cleaned: {nan_count}")

        # Temporal Alignment
        alignment_stats = results.get("alignment_stats", {})
        if alignment_stats:
            aligned_count = alignment_stats.get('aligned_count', 0)
            alignment_rate = alignment_stats.get('alignment_rate', '0%')
            print(f"\n⏰ Temporal Alignment:")
            print(f"   Aligned: {aligned_count} ({alignment_rate})")

        # Deduplication
        dedup_stats = results.get("dedup_stats", {})
        if dedup_stats:
            duplicates_removed = dedup_stats.get('duplicates_removed', 0)
            unique_records = dedup_stats.get('unique_records', 0)
            print(f"\n🔍 Deduplication:")
            print(f"   Duplicates removed: {duplicates_removed}")
            print(f"   Unique records: {unique_records}")

        # Quality Assurance
        qa_stats = results.get("qa_stats", {})
        if qa_stats:
            qa_passed = qa_stats.get('qa_passed', 0)
            qa_failed = qa_stats.get('qa_failed', 0)
            pass_rate = qa_stats.get('pass_rate', '0%')
            threshold_met = qa_stats.get('threshold_met', False)
            
            print(f"\n✔️  Quality Assurance:")
            print(f"   Passed: {qa_passed}")
            print(f"   Failed: {qa_failed}")
            print(f"   Pass rate: {pass_rate}")
            print(f"   Threshold: {'✅ Met' if threshold_met else '⚠️  Not Met'}")

        # Export
        export_stats = results.get("export_stats", {})
        if export_stats:
            records_exported = export_stats.get('records_exported', 0)
            exported_files = export_stats.get('exported_files', [])
            output_dir = export_stats.get('output_directory', 'N/A')
            
            print(f"\n📦 Export:")
            print(f"   Records: {records_exported}")
            print(f"   Files: {len(exported_files)}")
            print(f"   Directory: {output_dir}")

            # Show first few files
            if exported_files:
                print(f"\n   Sample Files:")
                for file_path in exported_files[:5]:
                    print(f"      • {Path(file_path).name}")
                if len(exported_files) > 5:
                    print(f"      ... and {len(exported_files) - 5} more")

        # Duration
        pipeline_duration = results.get("pipeline_duration", 0)
        print(f"\n⏱️  Duration: {pipeline_duration:.2f}s")

        # Final Status
        print("\n" + "="*80)
        print("✅ PIPELINE COMPLETED SUCCESSFULLY")
        print("="*80)

        # Log locations
        print("\n📝 Logs available at:")
        print("   • logs/pipeline/")
        print("   • logs/stages/")
        print("   • logs/adapters/")
        print("   • logs/errors/")
        print()

        log_event(
            stage="pipeline",
            block="run_script",
            level="INFO",
            msg="Pipeline completed successfully",
            extra={"duration": pipeline_duration},
        )

    except Exception as e:
        print("\n" + "="*80)
        print("❌ PIPELINE FAILED")
        print("="*80)
        print(f"\nError: {str(e)}\n")
        
        import traceback
        traceback.print_exc()
        
        log_event(
            stage="pipeline",
            block="run_script",
            level="ERROR",
            msg=f"Pipeline failed: {str(e)}",
        )
        
        sys.exit(1)


def main():
    """Main execution function"""
    asyncio.run(run_complete_pipeline())


if __name__ == "__main__":
    main()