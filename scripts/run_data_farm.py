"""
Run script for ResilientDataFarm
Entry point to execute the data pipeline and smoke tests
"""

from pathlib import Path
import sys
import asyncio

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from marketpilot.data_farm.resilient_data_farm import ResilientDataFarm
from marketpilot.utils.logger import log_event


async def run_smoke_test():
    """Main execution function"""
    try:
        log_event(
            stage="pipeline",
            block="run_script",
            level="INFO",
            msg="Starting Data Farm smoke test (MP-006)",
        )

        # Initialize Data Farm
        farm = ResilientDataFarm(
            config_path="src/marketpilot/config/data_farm_config.yaml"
        )

        print("\n✅ Data Farm initialized successfully!")
        print(f"📊 Loaded {len(farm.get_adapters())} adapter(s)")

        # Run smoke test with 3 assets
        test_symbols = ["AAPL", "NVDA", "TSLA"]
        print(f"\n🧪 Running smoke test for: {', '.join(test_symbols)}")
        print("=" * 60)

        results = await farm.run_smoke_test(test_symbols)

        # Print results
        print("\n📋 SMOKE TEST RESULTS:")
        print(f"   Total Tests: {results['total_tests']}")
        print(f"   ✅ Passed: {results['passed']}")
        print(f"   ❌ Failed: {results['failed']}")
        print("\n" + "=" * 60)

        # Print details
        print("\n📝 Detailed Results:")
        for detail in results["details"]:
            status = detail["status"]
            adapter = detail["adapter_id"]
            symbol = detail["symbol"]
            print(f"   {status} - {adapter} - {symbol}")
            if "error" in detail:
                print(f"      Error: {detail['error']}")

        print("\n" + "=" * 60)

        # Final verdict
        if results["failed"] == 0:
            print("\n🎉 ALL TESTS PASSED - Environment is stable!")
            log_event(
                stage="pipeline",
                block="run_script",
                level="INFO",
                msg="Smoke test completed successfully",
                extra=results,
            )
        else:
            print(f"\n⚠️  {results['failed']} test(s) failed - Check logs for details")
            log_event(
                stage="pipeline",
                block="run_script",
                level="WARNING",
                msg="Smoke test completed with failures",
                extra=results,
            )

        print("\n📝 Check logs/ directory or detailed logs")
        print("   - logs/pipeline/")
        print("   - logs/adapters/")
        print("   - logs/stages/")
        print("   - logs/errors/")

    except Exception as e:
        log_event(
            stage="pipeline",
            block="run_script",
            level="ERROR",
            msg=f"Smoke test failed: {str(e)}",
        )
        print(f"\n❌ Test execution failed: {e}")
        sys.exit(1)


def main():
    """Main execution function"""
    asyncio.run(run_smoke_test())


if __name__ == "__main__":
    main()
