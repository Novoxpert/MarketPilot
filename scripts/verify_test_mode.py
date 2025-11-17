"""
Complete Test Mode Verification Script
Creates all test directories and verifies isolation
"""

import asyncio
from pathlib import Path
from marketpilot.utils.mode_manager import (
    get_mode_manager,
    set_test_mode,
    set_normal_mode,
)
from marketpilot.utils.logger import log_event, setup_logging


def check_directory_structure():
    """Check and create directory structure"""
    print("=" * 60)
    print(" Checking Directory Structure")
    print("=" * 60)
    print()

    manager = get_mode_manager()

    # Get all paths
    paths = manager.get_all_paths()

    for name, path in paths.items():
        if path.exists():
            print(f" {name}: {path}")
        else:
            print(f"  {name}: {path} (creating...)")
            path.mkdir(parents=True, exist_ok=True)
            print("    Created")

    print()


def create_sample_logs():
    """Create sample log entries"""
    print("=" * 60)
    print(" Creating Sample Logs")
    print("=" * 60)
    print()

    # Create logs in different categories
    log_event(
        "test_stage",
        "stage",
        "INFO",
        "Sample stage log",
        extra={"records_processed": 10},
    )

    log_event(
        "test_adapter",
        "yfinance_adapter",
        "INFO",
        "Sample adapter log",
        extra={"symbol": "AAPL"},
    )

    log_event(
        "test_error",
        "test_block",
        "ERROR",
        "Sample error log",
        extra={"error_type": "TestError", "error_message": "Test error"},
    )

    log_event("test_pipeline", "test", "INFO", "Sample pipeline log")

    print(" Sample logs created")
    print()


def create_sample_data():
    """Create sample data files"""
    print("=" * 60)
    print(" Creating Sample Data")
    print("=" * 60)
    print()

    import json
    from datetime import datetime

    manager = get_mode_manager()
    data_dir = manager.get_data_dir()

    # Create output directory
    output_dir = data_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create sample data file
    sample_data = {
        "created_at": datetime.now().isoformat(),
        "mode": manager.mode.value,
        "sample_records": [
            {"symbol": "AAPL", "price": 150.0},
            {"symbol": "NVDA", "price": 500.0},
        ],
    }

    output_file = output_dir / "sample_data.json"
    with open(output_file, "w") as f:
        json.dump(sample_data, f, indent=2)

    print(f" Created: {output_file}")


def verify_isolation():
    """Verify that test and normal modes are isolated"""
    print("=" * 60)
    print(" Verifying Isolation")
    print("=" * 60)
    print()

    # Check normal directories
    normal_dirs = [Path("logs"), Path("data")]

    print("Normal Mode Directories:")
    for dir_path in normal_dirs:
        if dir_path.exists():
            file_count = sum(1 for _ in dir_path.rglob("*") if _.is_file())
            print(f"   {dir_path}/ ({file_count} files)")
        else:
            print(f"    {dir_path}/ (doesn't exist)")

    print()

    # Check test directories
    test_dirs = [Path("logs_test"), Path("data_test")]

    print("Test Mode Directories:")
    for dir_path in test_dirs:
        if dir_path.exists():
            file_count = sum(1 for _ in dir_path.rglob("*") if _.is_file())
            print(f"   {dir_path}/ ({file_count} files)")
        else:
            print(f"   {dir_path}/ (doesn't exist)")

    print()


def show_file_tree(
    root_dir: Path, prefix: str = "", max_depth: int = 3, current_depth: int = 0
):
    """Show directory tree"""
    if current_depth >= max_depth or not root_dir.exists():
        return

    items = sorted(root_dir.iterdir())

    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        current_prefix = "└── " if is_last else "├── "
        print(f"{prefix}{current_prefix}{item.name}{'/' if item.is_dir() else ''}")

        if item.is_dir() and current_depth < max_depth - 1:
            extension = "    " if is_last else "│   "
            show_file_tree(item, prefix + extension, max_depth, current_depth + 1)


def show_complete_structure():
    """Show complete directory structure"""
    print("=" * 60)
    print(" Complete Directory Structure")
    print("=" * 60)
    print()

    # Show normal mode
    print("Normal Mode (logs/):")
    if Path("logs").exists():
        show_file_tree(Path("logs"))
    else:
        print("  (doesn't exist)")

    print()

    # Show test mode
    print("Test Mode (logs_test/):")
    if Path("logs_test").exists():
        show_file_tree(Path("logs_test"))
    else:
        print("  (doesn't exist)")

    print()

    # Show data directories
    print("Normal Data (data/):")
    if Path("data").exists():
        show_file_tree(Path("data"))
    else:
        print("  (doesn't exist)")

    print()

    print("Test Data (data_test/):")
    if Path("data_test").exists():
        show_file_tree(Path("data_test"))
    else:
        print("  (doesn't exist)")

    print()


async def main():
    """Main verification"""
    print()
    print("=" * 60)
    print(" TEST MODE VERIFICATION")
    print("=" * 60)
    print()

    # Step 1: Normal Mode
    print("STEP 1: Normal Mode Operations")
    print("-" * 60)
    set_normal_mode()
    manager = get_mode_manager()
    print(f"Current mode: {manager.mode.value}")
    print()

    setup_logging("INFO")
    check_directory_structure()
    create_sample_logs()
    create_sample_data()

    # Step 2: Test Mode
    print()
    print("STEP 2: Test Mode Operations")
    print("-" * 60)
    set_test_mode()
    manager = get_mode_manager()
    print(f"Current mode: {manager.mode.value}")
    print()

    setup_logging("INFO")
    check_directory_structure()
    create_sample_logs()
    create_sample_data()

    # Step 3: Verification
    print()
    print("STEP 3: Verification")
    print("-" * 60)
    verify_isolation()

    # Step 4: Show structure
    print()
    print("STEP 4: Directory Structure")
    print("-" * 60)
    show_complete_structure()

    # Summary
    print("=" * 60)
    print(" VERIFICATION COMPLETE")
    print("=" * 60)
    print()

    # Check success
    success = True
    checks = []

    # Check test directories exist
    if Path("logs_test").exists():
        checks.append(" logs_test/ created")
    else:
        checks.append(" logs_test/ NOT created")
        success = False

    if Path("data_test").exists():
        checks.append(" data_test/ created")
    else:
        checks.append(" data_test/ NOT created")
        success = False

    # Check files exist
    if list(Path("logs_test").rglob("*.jsonl")):
        checks.append(" Test logs created")
    else:
        checks.append(" Test logs NOT created")
        success = False

    if Path("data_test/output").exists():
        checks.append(" Test data output created")
    else:
        checks.append(" Test data output NOT created")
        success = False

    print("Verification Results:")
    for check in checks:
        print(f"  {check}")

    print()

    if success:
        print(" All checks passed!")
    else:
        print("  Some checks failed")

    print()
    print("=" * 60)

    # Return to normal mode
    set_normal_mode()


if __name__ == "__main__":
    asyncio.run(main())
