"""
Example: Run Data Farm Smoke Test

This example demonstrates how to run a quick smoke test to verify
that all adapters are working correctly before running the full pipeline.

Usage:
    python run_smoke_test.py
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
    Run smoke test example
    
    Steps:
    1. Initialize ResilientDataFarm
    2. Define test parameters
    3. Run smoke test
    4. Display results
    """
    
    print("\n" + "="*60)
    print("ResilientDataFarm - Smoke Test Example")
    print("="*60 + "\n")
    
    # ============================================================
    # 1. Initialize Data Farm
    # ============================================================
    print("Step 1: Initializing ResilientDataFarm...")
    farm = ResilientDataFarm()
    
    adapters = farm.get_adapters()
    print(f"   Loaded {len(adapters)} adapters:")
    for adapter in adapters:
        print(f"      - {adapter.adapter_id} ({adapter.__class__.__name__})")
    print()
    
    # ============================================================
    # 2. Define Test Parameters
    # ============================================================
    print("Step 2: Defining smoke test parameters...")
    
    # Define test symbols (only first one will be used)
    test_symbols = [
        "BINANCE:BTCUSDT.P",
        "BINANCE:ETHUSDT.P",
    ]
    
    # Define optional date range for testing
    start_date = datetime.strptime("2025-11-27 07:08", "%Y-%m-%d %H:%M")
    end_date = datetime.strptime("2025-12-01 13:09", "%Y-%m-%d %H:%M")
    
    print(f"   Test Symbol: {test_symbols[0]}")
    print(f"   Start: {start_date.isoformat() if start_date else 'Not specified'}")
    print(f"   End: {end_date.isoformat() if end_date else 'Not specified'}\n")
    
    # ============================================================
    # 3. Run Smoke Test
    # ============================================================
    print("Step 3: Running smoke test...")
    print("   Testing each adapter with single symbol...\n")
    
    results = await farm.run_smoke_test(
        symbols=test_symbols,
        start=start_date,
        end=end_date
    )
    
    # ============================================================
    # 4. Display Results
    # ============================================================
    print("\n" + "="*60)
    print("Smoke Test Results")
    print("="*60 + "\n")
    
    # Summary
    total = results.get("total_tests", 0)
    passed = results.get("passed", 0)
    failed = results.get("failed", 0)
    success = results.get("success", False)
    
    print(f"Overall Status: {'PASSED' if success else 'FAILED'}\n")
    print("Summary:")
    print(f"   - Total Tests: {total}")
    print(f"   - Passed: {passed}")
    print(f"   - Failed: {failed}")
    print(f"   - Success Rate: {(passed/total*100) if total > 0 else 0:.1f}%\n")
    
    # Detailed results
    print("Detailed Results:\n")
    
    details = results.get("details", [])
    for detail in details:
        adapter_id = detail.get("adapter_id", "Unknown")
        symbol = detail.get("symbol", "N/A")
        status = detail.get("status", "UNKNOWN")
        
        if status == "PASSED":
            icon = "-"
            record_count = detail.get("record_count", 0)
            print(f"   {icon} {adapter_id}")
            print(f"      Symbol: {symbol}")
            print(f"      Records: {record_count:,}")
        
        elif status == "FAILED":
            icon = "x"
            error = detail.get("error", "Unknown error")
            print(f"   {icon} {adapter_id}")
            print(f"      Symbol: {symbol}")
            print(f"      Error: {error}")
        
        elif status == "EXCEPTION":
            icon = "!"
            error = detail.get("error", "Unknown exception")
            print(f"   {icon} {adapter_id}")
            print(f"      Symbol: {symbol}")
            print(f"      Exception: {error}")
        
        print()
    
    # ============================================================
    # 5. Recommendations
    # ============================================================
    if not success:
        print("="*60)
        print("Recommendations")
        print("="*60 + "\n")
        print("Some adapters failed the smoke test.")
        print("Please check the following before running full pipeline:\n")
        
        for detail in details:
            if detail.get("status") != "PASSED":
                adapter_id = detail.get("adapter_id")
                print(f"   - Fix adapter: {adapter_id}")
        
        print("\nCommon issues:")
        print("   - API credentials not configured")
        print("   - Network connectivity problems")
        print("   - Invalid symbol format")
        print("   - API rate limits exceeded\n")
    
    else:
        print("="*60)
        print("All adapters are working correctly!")
        print("="*60 + "\n")
        print("You can now run the full pipeline with confidence.\n")
        print("Next step: python run_pipeline.py\n")
    
    print("="*60 + "\n")
    
    return success


if __name__ == "__main__":
    """
    Run the smoke test example
    """
    try:
        success = asyncio.run(main())
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\nSmoke test interrupted by user")
        sys.exit(130)
        
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        raise
