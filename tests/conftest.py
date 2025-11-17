"""
Pytest Configuration
Automatically sets test mode for all pytest tests
"""

import pytest
from marketpilot.utils.mode_manager import set_test_mode, reset_mode, get_mode_manager
from marketpilot.utils.logger import setup_logging


@pytest.fixture(scope="session", autouse=True)
def test_mode_session():
    """
    Automatically enable test mode for entire pytest session
    This ensures all tests use logs_test/ directory
    """
    # Set test mode at start of session
    set_test_mode()

    #  Setup logging ONCE for entire test session
    setup_logging("INFO")

    manager = get_mode_manager()

    print("\n{'='*60}")
    print(" TEST MODE ACTIVATED")
    print("{'='*60}")
    print(f"Mode: {manager.mode.value}")
    print(f"Log Directory: {manager.get_log_dir()}")
    print(f"Data Directory: {manager.get_data_dir()}")
    print("{'='*60}\n")

    yield  # Run all tests

    # Reset to normal mode after all tests
    reset_mode()
    print(f"\n{'='*60}")
    print(" TEST SESSION COMPLETE - Restored to normal mode")
    print(f"{'='*60}\n")


@pytest.fixture(autouse=True)
def log_test_info(request):
    """
    Log information about each test
    Runs automatically for every test
    """
    test_name = request.node.name
    print(f"\n  Running: {test_name}")

    yield


@pytest.fixture
def sample_adapters():
    """Provide sample adapter data for tests"""
    return [
        {"adapter_id": "test_adapter_1", "type": "price"},
        {"adapter_id": "test_adapter_2", "type": "price"},
    ]


@pytest.fixture
def sample_symbols():
    """Provide sample symbol list for tests"""
    return ["AAPL", "GOOGL", "MSFT"]


@pytest.fixture
def sample_price_data():
    """Provide sample price data for tests"""
    return [
        {
            "symbol": "AAPL",
            "timestamp": "2024-01-01T00:00:00",
            "open": 150.0,
            "high": 155.0,
            "low": 149.0,
            "close": 154.0,
            "volume": 1000000,
        },
        {
            "symbol": "GOOGL",
            "timestamp": "2024-01-01T00:00:00",
            "open": 100.0,
            "high": 105.0,
            "low": 99.0,
            "close": 104.0,
            "volume": 500000,
        },
    ]


# Optional: Clean up test logs after each test session
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_logs():
    """Clean up test logs after session (optional)"""
    yield  # Run all tests first

    # Uncomment below to auto-clean test logs after each run
    # from pathlib import Path
    # import shutil
    # test_log_dir = Path("logs_test")
    # if test_log_dir.exists():
    #     print(f"\n Cleaning up test logs: {test_log_dir}")
    #     shutil.rmtree(test_log_dir)
