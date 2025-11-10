"""
Example Script: Enhanced Logging Demo
Demonstrates the new logging capabilities
"""

import asyncio
import json
from pathlib import Path
from marketpilot.data_farm.resilient_data_farm import ResilientDataFarm
from marketpilot.utils.log_validator import LogValidator


async def main():
    """Run pipeline and validate logs"""

    # Clean old logs (optional)
    # import shutil
    # if Path("logs").exists():
    #     shutil.rmtree("logs")

    # Initialize Data Farm
    print("📦 Initializing Data Farm...")
    farm = ResilientDataFarm()
    print()

    # Run smoke test
    print("🚀 Running smoke test...")
    symbols = ["AAPL", "NVDA"]
    results = await farm.run_smoke_test(symbols)
    print(f"✅ Smoke test complete: {results['passed']}/{results['total_tests']} passed")
    print()

    # Show log directory structure
    print("=" * 60)
    print("📁 Log Directory Structure")
    print("=" * 60)
    print()

    log_dir = Path("logs")
    if log_dir.exists():
        for subdir in ["pipeline", "stages", "adapters", "errors"]:
            subdir_path = log_dir / subdir
            if subdir_path.exists():
                files = list(subdir_path.glob("*.jsonl"))
                print(f"  {subdir}/")
                for file in files:
                    size = file.stat().st_size
                    print(f"    └── {file.name} ({size} bytes)")
        print()
    else:
        print("  No logs directory found")
        print()

    # Validate logs
    print("=" * 60)
    print("🔍 Validating Log Files")
    print("=" * 60)
    print()

    validator = LogValidator()
    report = validator.validate_all_logs()

    print(f"Total Files: {report['summary']['total_files']}")
    print(f"Valid Files: {report['summary']['valid_files']}")
    print(f"Invalid Files: {report['summary']['invalid_files']}")
    print(f"Total Entries: {report['summary']['total_entries']}")
    print(f"Malformed Entries: {report['summary']['malformed_entries']}")
    print()

    if report["overall_valid"]:
        print("✅ All log files are properly formatted!")
    else:
        print("❌ Some log files have issues:")
        for file_report in report["files_validated"]:
            if not file_report["valid"]:
                print(f"\n  {file_report['file']}:")
                if file_report["malformed_entries"]:
                    print(
                        f"    - {len(file_report['malformed_entries'])} malformed entries"
                    )
                if file_report["missing_fields"]:
                    print(
                        f"    - {len(file_report['missing_fields'])} entries with missing fields"
                    )

    print()

    # Show sample log entries
    print("=" * 60)
    print("📋 Sample Log Entries")
    print("=" * 60)
    print()

    # Show adapter log sample
    adapter_logs = list(Path("logs/adapters").glob("*.jsonl"))
    if adapter_logs:
        print("Adapter Log Sample:")
        print("-" * 60)
        with open(adapter_logs[0], "r", encoding="utf-8") as f:
            lines = f.readlines()
            if lines:
                sample = json.loads(lines[-1])
                print(json.dumps(sample, indent=2))
        print()

    # Show stage log sample
    stage_logs = list(Path("logs/stages").glob("*.jsonl"))
    if stage_logs:
        print("Stage Log Sample:")
        print("-" * 60)
        with open(stage_logs[0], "r", encoding="utf-8") as f:
            lines = f.readlines()
            if lines:
                sample = json.loads(lines[-1])
                print(json.dumps(sample, indent=2))
        print()

    # Save validation report
    report_path = Path("logs/validation_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("=" * 60)
    print(f"💾 Validation report saved: {report_path}")
    print("=" * 60)
    print()

    # Show metrics summary
    print("=" * 60)
    print("📊 Logging Metrics Summary")
    print("=" * 60)
    print()

    # Count operations by type
    operation_counts = {"stage": 0, "adapter": 0, "error": 0}
    total_duration = 0
    successful_ops = 0
    failed_ops = 0

    for log_file in log_dir.rglob("*.jsonl"):
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)

                    # Count by block type
                    if "adapter" in entry.get("block", "").lower():
                        operation_counts["adapter"] += 1
                    elif entry.get("block") == "stage":
                        operation_counts["stage"] += 1

                    # Count errors
                    if entry.get("level") == "ERROR":
                        operation_counts["error"] += 1

                    # Sum durations
                    extra = entry.get("extra", {})
                    if "duration_ms" in extra:
                        total_duration += extra["duration_ms"]

                    # Count successes/failures
                    if "success_flag" in extra:
                        if extra["success_flag"]:
                            successful_ops += 1
                        else:
                            failed_ops += 1

                except json.JSONDecodeError:
                    pass

    print("Total Operations Logged:")
    print(f"  Stage Operations: {operation_counts['stage']}")
    print(f"  Adapter Operations: {operation_counts['adapter']}")
    print(f"  Error Entries: {operation_counts['error']}")
    print()
    print("Operation Results:")
    print(f"  Successful: {successful_ops}")
    print(f"  Failed: {failed_ops}")
    print()
    print("Performance:")
    print(f"  Total Duration: {total_duration:.2f} ms")
    if successful_ops > 0:
        print(f"  Average Duration: {total_duration / successful_ops:.2f} ms")
    print()

    print("=" * 60)
    print("✅ Logging demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
