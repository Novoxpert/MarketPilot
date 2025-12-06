"""
Example: Run Complete Data Farm Pipeline

This example demonstrates how to run the full ResilientDataFarm pipeline
to collect, process, and export market data.

Usage:
    python run_pipeline.py
"""

import asyncio
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path if needed
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from marketpilot.data_farm.resilient_data_farm import ResilientDataFarm


async def main():
    """
    Run complete data pipeline example
    
    Steps:
    1. Initialize ResilientDataFarm
    2. Define symbols and date range
    3. Run complete pipeline
    4. Display results
    """
    
    print("\n" + "="*60)
    print("🚀 ResilientDataFarm - Complete Pipeline Example")
    print("="*60 + "\n")
    
    # ============================================================
    # 1. Initialize Data Farm
    # ============================================================
    print("📋 Step 1: Initializing ResilientDataFarm...")
    farm = ResilientDataFarm()
    print(f"   ✓ Loaded {len(farm.get_adapters())} adapters\n")
    
    # ============================================================
    # 2. Define Parameters
    # ============================================================
    print("📋 Step 2: Defining pipeline parameters...")
    
    # Define symbols to process
    symbols = [
        "BINANCE:BTCUSDT.P",
        "BINANCE:ETHUSDT.P",
    ]
    
    # Define optional date range
    start_date = datetime.strptime("2025-11-01 07:08", "%Y-%m-%d %H:%M")
    end_date = datetime.strptime("2025-12-01 07:09", "%Y-%m-%d %H:%M")
    
    # Or use None for default ranges
    # start_date = None
    # end_date = None
    
    print(f"   Symbols: {symbols}")
    print(f"   Start: {start_date.isoformat() if start_date else 'Default'}")
    print(f"   End: {end_date.isoformat() if end_date else 'Default'}\n")
    
    # ============================================================
    # 3. Run Complete Pipeline
    # ============================================================
    print("📋 Step 3: Running complete pipeline...")
    print("   This will execute all stages:")
    print("   → Health Check")
    print("   → Data Collection")
    print("   → NaN Processing")
    print("   → Temporal Alignment")
    print("   → Deduplication")
    print("   → Quality Assurance")
    print("   → Data Export\n")
    
    results = await farm.run_complete_pipeline(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date
    )
    
    # ============================================================
    # 4. Display Results
    # ============================================================
    print("\n" + "="*60)
    print("📊 Pipeline Results")
    print("="*60 + "\n")
    
    if results.get("pipeline_success"):
        print("✅ Pipeline completed successfully!\n")
        
        # Basic stats
        duration = results.get("pipeline_duration", 0)
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"📦 Symbols Processed: {len(symbols)}")
        
        # Export stats
        export_stats = results.get("export_stats", {})
        records_exported = export_stats.get("records_exported", 0)
        files_created = export_stats.get("files_created", 0)
        
        print(f"📝 Records Exported: {records_exported:,}")
        print(f"📁 Files Created: {files_created}")
        
        # Collection summary
        collection = results.get("collection_summary", {})
        if collection:
            print(f"\n📥 Collection Summary:")
            print(f"   • Successful: {collection.get('successful', 0)}")
            print(f"   • Failed: {collection.get('failed', 0)}")
            print(f"   • Total Records: {collection.get('total_records', 0):,}")
        
        # Quality metrics
        qa_results = results.get("qa_results", {})
        if qa_results:
            print(f"\n✓ Quality Assurance:")
            print(f"   • Status: {qa_results.get('overall_status', 'N/A')}")
            print(f"   • Checks Passed: {qa_results.get('checks_passed', 0)}")
            print(f"   • Checks Failed: {qa_results.get('checks_failed', 0)}")
        
    else:
        print("❌ Pipeline failed!\n")
        error = results.get("error", "Unknown error")
        duration = results.get("pipeline_duration", 0)
        
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"❗ Error: {error}")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    """
    Run the example
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        raise