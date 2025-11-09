"""
Simple unit tests for pipeline stages (MP-007)
Basic tests to verify stage functionality
"""

import asyncio
from marketpilot.data_farm.stages.health_check import HealthCheckStage
from marketpilot.data_farm.stages.data_collection import DataCollectionStage
from marketpilot.data_farm.stages.nan_processing import NaNProcessingStage
from marketpilot.data_farm.stages.deduplication import DeduplicationStage


def test_health_check_basic():
    """Test basic health check"""
    print("\n🧪 Testing Health Check Stage...")

    async def run_test():
        stage = HealthCheckStage()
        data = {
            "adapters": [{"adapter_id": "test_1"}],
            "config": {},
        }

        result = await stage.execute(data)
        assert "health_check" in result
        assert result["health_check"]["total_adapters"] == 1
        print("   ✅ Health check passed")

    asyncio.run(run_test())


def test_data_collection_empty():
    """Test data collection with no adapters"""
    print("\n🧪 Testing Data Collection Stage (empty)...")

    async def run_test():
        stage = DataCollectionStage()
        data = {
            "adapters": [],
            "symbols": ["AAPL"],
        }

        result = await stage.execute(data)
        assert "raw_data" in result
        assert len(result["raw_data"]) == 0
        print("   ✅ Data collection handled empty input")

    asyncio.run(run_test())


def test_nan_processing_basic():
    """Test NaN processing"""
    print("\n🧪 Testing NaN Processing Stage...")

    async def run_test():
        stage = NaNProcessingStage()
        data = {
            "raw_data": [
                {
                    "symbol": "AAPL",
                    "data": {
                        "open": 150.0,
                        "close": None,  # NaN value
                    },
                }
            ]
        }

        result = await stage.execute(data)
        assert "processed_data" in result
        assert "nan_stats" in result
        # Check that None was replaced
        assert result["processed_data"][0]["data"]["close"] == 0
        print("   ✅ NaN processing replaced None values")

    asyncio.run(run_test())


def test_deduplication_basic():
    """Test deduplication"""
    print("\n🧪 Testing Deduplication Stage...")

    async def run_test():
        stage = DeduplicationStage()
        data = {
            "aligned_data": [
                {
                    "adapter_id": "test_1",
                    "symbol": "AAPL",
                    "data": {"timestamp": "2024-01-01T00:00:00"},
                },
                {
                    "adapter_id": "test_1",
                    "symbol": "AAPL",
                    "data": {"timestamp": "2024-01-01T00:00:00"},
                },  # Duplicate
            ]
        }

        result = await stage.execute(data)
        assert "unique_data" in result
        assert "dedup_stats" in result
        assert len(result["unique_data"]) == 1
        assert result["dedup_stats"]["duplicates_removed"] == 1
        print("   ✅ Deduplication removed duplicate records")

    asyncio.run(run_test())


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🧪 RUNNING SIMPLE UNIT TESTS")
    print("=" * 60)

    try:
        test_health_check_basic()
        test_data_collection_empty()
        test_nan_processing_basic()
        test_deduplication_basic()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60 + "\n")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        raise


if __name__ == "__main__":
    main()
