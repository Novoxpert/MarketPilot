"""
Example: Using Test vs Normal Mode
Demonstrates how mode isolation works
"""

import asyncio
from marketpilot.utils.mode_manager import (
    get_mode_manager,
    set_test_mode,
    set_normal_mode,
)
from marketpilot.utils.logger import log_event, setup_logging


async def run_sample_operations(mode_name: str):
    """Run sample operations in current mode"""
    print(f"\n{'=' * 60}")
    print(f"Running in {mode_name.upper()} mode")
    print("=" * 60)

    manager = get_mode_manager()

    # Show current settings
    print(f"\nMode: {manager.mode.value}")
    print(f"Log directory: {manager.get_log_dir()}")
    print(f"Data directory: {manager.get_data_dir()}")
    print(f"Config file: {manager.get_config_file()}")

    # Setup logging
    setup_logging("INFO")

    # Log some events
    print("\nLogging events...")
    log_event("sample", "sample_block", "INFO", f"Sample info log in {mode_name} mode")
    log_event(
        "sample", "sample_block", "WARNING", f"Sample warning in {mode_name} mode"
    )
    log_event(
        "sample",
        "sample_block",
        "ERROR",
        f"Sample error in {mode_name} mode",
        extra={"error_type": "SampleError"},
    )

    # Check log files
    print("\nLog files created:")
    log_dir = manager.get_log_dir()
    if log_dir.exists():
        for log_file in log_dir.rglob("*.jsonl"):
            print(f"   {log_file}")
    else:
        print("    No log directory yet")

    print()


async def main():
    """Main demo"""
    print("=" * 60)
    print("TEST vs NORMAL Mode Demo")
    print("=" * 60)

    # Run in normal mode
    set_normal_mode()
    await run_sample_operations("normal")

    # Run in test mode
    set_test_mode()
    await run_sample_operations("test")

    # Show comparison
    print("=" * 60)
    print("Directory Comparison")
    print("=" * 60)
    print()

    from pathlib import Path

    print("Normal Mode:")
    print("  logs/")
    if Path("logs").exists():
        for item in sorted(Path("logs").iterdir()):
            if item.is_dir():
                print(f"    {item.name}/")

    print()
    print("Test Mode:")
    print("  logs_test/")
    if Path("logs_test").exists():
        for item in sorted(Path("logs_test").iterdir()):
            if item.is_dir():
                print(f"    {item.name}/")
    else:
        print("    (not created yet)")

    print()
    print("=" * 60)
    print(" Demo complete!")
    print("=" * 60)
    print()
    print("Key Benefits:")
    print("   Isolated logging (logs vs logs_test)")
    print("   Isolated data (data vs data_test)")
    print("   No production data contamination")
    print("   Test data preserved for debugging")
    print("   Automatic in pytest via conftest.py")
    print()
    print("Note:")
    print("   Test directories preserved (not deleted)")
    print("    To cleanup: rm -rf logs_test/ data_test/")
    print()

    # Return to normal mode (don't cleanup)
    set_normal_mode()


if __name__ == "__main__":
    asyncio.run(main())
