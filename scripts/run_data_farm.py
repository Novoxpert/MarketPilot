"""
Complete Data Farm Pipeline Runner with Time Range
Executes full pipeline for multiple symbols with custom date range
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from marketpilot.data_farm.resilient_data_farm import ResilientDataFarm
from marketpilot.utils.logger import log_event


async def run_pipeline_with_timerange(
    symbols: List[str],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    config_path: str = "src/marketpilot/configs/data/data_farm_config.yml",
    run_smoke_test: bool = True
):
    """
    Run complete data farm pipeline for specific symbols and time range
    
    Args:
        symbols: List of symbols to fetch (e.g., ["AAPL", "MSFT", "NVDA"])
        start_date: Start datetime for data collection (None = use adapter defaults)
        end_date: End datetime for data collection (None = use adapter defaults)
        config_path: Path to config file
        run_smoke_test: Whether to run smoke test first
    """
    print("\n" + "="*80)
    print("🚀 RESILIENT DATA FARM - COMPLETE PIPELINE")
    print("="*80)
    
    # Show configuration
    print(f"\n📊 Configuration:")
    print(f"   Symbols: {', '.join(symbols)}")
    
    if start_date and end_date:
        duration_hours = (end_date - start_date).total_seconds() / 3600
        print(f"   Time Range:")
        print(f"      Start: {start_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"      End:   {end_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"      Duration: {duration_hours:.1f} hours")
    else:
        print(f"   Time Range: Using adapter defaults")
    
    print(f"   Config: {config_path}")
    print(f"   Smoke Test: {'Enabled' if run_smoke_test else 'Disabled'}")
    print("\n" + "-"*80 + "\n")

    # ========================================
    # Step 1: Initialize Data Farm
    # ========================================
    print("🔧 Step 1/4: Initializing Data Farm...")
    try:
        farm = ResilientDataFarm(config_path=config_path)
        print(f"   ✅ Loaded {len(farm.adapters)} adapters")
        print(f"   ✅ Configured {len(farm.stages)} pipeline stages")
        
        # Show adapter details
        print(f"\n   Adapters:")
        for adapter in farm.adapters:
            print(f"      • {adapter.adapter_id} ({adapter.schema_type})")
        print()
        
    except Exception as e:
        print(f"   ❌ Initialization failed: {e}")
        return {"success": False, "error": str(e)}

    # ========================================
    # Step 2: Smoke Test (Optional)
    # ========================================
    if run_smoke_test:
        print("🏥 Step 2/4: Running Smoke Test...")
        try:
            smoke_results = await farm.run_smoke_test(symbols[:1])
            
            print(f"   Tests: {smoke_results['passed']}/{smoke_results['total_tests']} passed")
            
            if not smoke_results["success"]:
                print("\n   ❌ SMOKE TEST FAILED")
                print("\n   Failed Adapters:")
                for detail in smoke_results["details"]:
                    if detail["status"] != "PASSED":
                        print(f"      • {detail['adapter_id']}: {detail.get('error', 'Unknown')}")
                return {"success": False, "smoke_test": smoke_results}
            
            print("   ✅ All adapters operational\n")
            
        except Exception as e:
            print(f"   ❌ Smoke test exception: {e}")
            return {"success": False, "error": str(e)}
    else:
        print("🏥 Step 2/4: Smoke Test - Skipped\n")

    # ========================================
    # Step 3: Configure Time Range (if provided)
    # ========================================
    if start_date and end_date:
        print("⏰ Step 3/4: Configuring Time Range...")
        try:
            # Inject time range into adapter configs
            for adapter in farm.adapters:
                adapter.config["start"] = start_date
                adapter.config["end"] = end_date
            
            print(f"   ✅ Time range applied to all adapters\n")
        
        except Exception as e:
            print(f"   ❌ Time range configuration failed: {e}")
            return {"success": False, "error": str(e)}
    else:
        print("⏰ Step 3/4: Using Default Time Ranges\n")

    # ========================================
    # Step 4: Execute Pipeline
    # ========================================
    print("🚀 Step 4/4: Executing Complete Pipeline")
    print("-"*80)
    
    try:
        pipeline_start = datetime.utcnow()
        
        # Run pipeline with time range
        results = await farm.run_complete_pipeline(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date
        )
        
        pipeline_end = datetime.utcnow()
        duration = (pipeline_end - pipeline_start).total_seconds()
        
        print("\n" + "-"*80)
        
        # ========================================
        # Results Summary
        # ========================================
        if results.get("pipeline_success"):
            print("\n✅ PIPELINE COMPLETED SUCCESSFULLY")
            print(f"\n📈 Results Summary:")
            print(f"   Total Duration: {duration:.2f}s")
            print(f"   Symbols Processed: {len(symbols)}")
            
            # Health Check
            health = results.get("health_check", {})
            if health:
                print(f"\n   🏥 Health Check:")
                print(f"      • Status: {health.get('overall_status', 'unknown').upper()}")
                print(f"      • APIs Healthy: {health.get('apis_healthy', 0)}/{health.get('apis_checked', 0)}")
            
            # Data Collection
            collection = results.get("collection_summary", {})
            if collection:
                print(f"\n   📥 Data Collection:")
                print(f"      • Total Fetches: {collection.get('total_fetches', 0)}")
                print(f"      • Successful: {collection.get('successful', 0)}")
                print(f"      • Failed: {collection.get('failed', 0)}")
                print(f"      • Total Records: {collection.get('total_records', 0)}")
            
            # NaN Processing
            nan_stats = results.get("nan_stats", {})
            if nan_stats:
                print(f"\n   🧹 NaN Processing:")
                print(f"      • NaNs Cleaned: {nan_stats.get('nan_count', 0)}")
            
            # Temporal Alignment
            alignment = results.get("alignment_stats", {})
            if alignment:
                print(f"\n   ⏰ Temporal Alignment:")
                print(f"      • Records Aligned: {alignment.get('aligned_count', 0)}")
                print(f"      • Alignment Rate: {alignment.get('alignment_rate', 'N/A')}")
            
            # Deduplication
            dedup = results.get("dedup_stats", {})
            if dedup:
                print(f"\n   🔍 Deduplication:")
                print(f"      • Duplicates Removed: {dedup.get('duplicates_removed', 0)}")
                print(f"      • Unique Records: {dedup.get('unique_records', 0)}")
            
            # Quality Assurance
            qa = results.get("qa_stats", {})
            if qa:
                threshold_met = qa.get('threshold_met', False)
                print(f"\n   ✔️  Quality Assurance:")
                print(f"      • Passed: {qa.get('qa_passed', 0)}")
                print(f"      • Failed: {qa.get('qa_failed', 0)}")
                print(f"      • Pass Rate: {qa.get('pass_rate', 'N/A')}")
                print(f"      • Threshold: {'✅ Met' if threshold_met else '⚠️  Not Met'}")
            
            # Export
            export = results.get("export_stats", {})
            if export:
                print(f"\n   📦 Export:")
                print(f"      • Records Exported: {export.get('records_exported', 0)}")
                print(f"      • Files Created: {len(export.get('exported_files', []))}")
                print(f"      • Output: {export.get('output_directory', 'N/A')}")
            
            # Show errors if any
            errors = results.get("collection_errors", [])
            if errors:
                print(f"\n   ⚠️  Errors ({len(errors)}):")
                for err in errors[:5]:
                    print(f"      • {err.get('symbol')} ({err.get('data_type')}): {err.get('error')}")
                if len(errors) > 5:
                    print(f"      ... and {len(errors) - 5} more")
            
            print("\n" + "="*80)
            print("\n📝 Logs available at:")
            print("   • logs/pipeline/")
            print("   • logs/stages/")
            print("   • logs/adapters/")
            print()
            
            return {"success": True, "results": results}
        
        else:
            print("\n❌ PIPELINE FAILED")
            print(f"\n⚠️  Error: {results.get('error', 'Unknown error')}")
            print(f"   Duration: {duration:.2f}s")
            print("\n" + "="*80)
            return {"success": False, "results": results}
    
    except Exception as e:
        print(f"\n❌ Pipeline execution failed: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


async def main():
    """Main entry point"""
    
    # ========================================================================
    # CONFIGURATION - Edit these values
    # ========================================================================
    
    # Symbols to process
    SYMBOLS = [
        "BINANCE:BTCUSDT.P",
        "BINANCE:ETHUSDT.P",
        # Add more symbols as needed
    ]
    
    # Time range (optional - leave as None to use adapter defaults)
    END_DATE = datetime.utcnow()
    START_DATE = END_DATE - timedelta(hours=24)  # Last 24 hours
    
    # Or use specific dates:
    # START_DATE = datetime(2025, 1, 1, 0, 0, 0)
    # END_DATE = datetime(2025, 1, 7, 23, 59, 59)
    
    # Or use None for adapter defaults:
    # START_DATE = None
    # END_DATE = None
    
    # Config path
    CONFIG_PATH = "src/marketpilot/configs/data/data_farm_config.yml"
    
    # Run smoke test first?
    RUN_SMOKE_TEST = True
    
    # ========================================================================
    
    # Execute pipeline
    result = await run_pipeline_with_timerange(
        symbols=SYMBOLS,
        start_date=START_DATE,
        end_date=END_DATE,
        config_path=CONFIG_PATH,
        run_smoke_test=RUN_SMOKE_TEST
    )
    
    # Exit with appropriate code
    if result.get("success"):
        print("✅ Script completed successfully\n")
        sys.exit(0)
    else:
        print("❌ Script failed\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())