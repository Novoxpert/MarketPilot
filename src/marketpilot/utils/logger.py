"""
Mode-Aware Logging System
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from marketpilot.utils.mode_manager import get_mode_manager


# Log level mapping
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

# Track if base structure is initialized
_LOG_STRUCTURE_INITIALIZED = False


def _get_log_base_dir() -> Path:
    """Get base log directory based on mode"""
    return get_mode_manager().get_log_dir()


def _ensure_base_structure():
    """
    Create only the base directory structure.
    Individual log files will be created on-demand when log_event() is called.
    """
    global _LOG_STRUCTURE_INITIALIZED

    if _LOG_STRUCTURE_INITIALIZED:
        return

    base = _get_log_base_dir()

    # Create only base directories (no files)
    dirs = ["pipeline", "stages", "adapters", "errors"]
    for d in dirs:
        (base / d).mkdir(parents=True, exist_ok=True)

    _LOG_STRUCTURE_INITIALIZED = True


def _resolve_log_file(stage: str, block: str, level: str) -> Path:
    """
    Resolve log file path dynamically based on stage, block, and level.

    Args:
        stage: Stage name (e.g., 'data_collection', 'nan_processing')
        block: Block/component name (e.g., 'price_internal_001_adapter', 'cleaner')
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Path to the appropriate log file
    """
    base = _get_log_base_dir()

    # ---- ERRORS ALWAYS GO TO errors/current.jsonl ----
    if level in ("ERROR", "CRITICAL"):
        return base / "errors" / "current.jsonl"

    # ---- ADAPTERS: Detect by block name pattern ----
    # If block name contains "adapter" or ends with "_adapter"
    if "adapter" in block.lower() or block.endswith("_adapter"):
        # Use block name as filename
        # Example: "price_internal_001_adapter" -> adapters/price_internal_001_adapter.jsonl
        return base / "adapters" / f"{block}.jsonl"

    # ---- STAGES ----
    known_stage_names = [
        "health_check",
        "data_collection",
        "nan_processing",
        "temporal_alignment",
        "deduplication",
        "quality_assurance",
        "data_export",
    ]

    if stage in known_stage_names:
        return base / "stages" / f"{stage}.jsonl"

    # ---- DEFAULT: pipeline/current.jsonl ----
    return base / "pipeline" / "current.jsonl"


def log_event(
    stage: str,
    block: str,
    level: str = "INFO",
    msg: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log an event to the appropriate JSONL file.
    Args:
        stage: Stage name (e.g., 'data_collection')
        block: Block/component name (e.g., 'price_internal_001_adapter')
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        msg: Log message
        extra: Additional fields to include in log entry

    Example:
        log_event("data_collection", "price_internal_001_adapter", "INFO",
                  "Fetched 100 records", {"symbol": "BINANCE:BTCUSDT.P"})
    """
    # Ensure base directories exist (only once)
    _ensure_base_structure()

    # Build log entry
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "stage": stage,
        "block": block,
        "level": level,
        "message": msg,
    }

    # Add mode info in test mode
    mode_manager = get_mode_manager()
    if mode_manager.is_test_mode:
        log_entry["test_mode"] = True

    # Add extra fields (e.g., symbol, adapter_id, records_count)
    if extra:
        log_entry.update(extra)

    # Resolve log file path
    log_file = _resolve_log_file(stage, block, level)

    # Ensure parent directory exists (should already exist from _ensure_base_structure)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Append to log file (creates file if doesn't exist)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, default=str) + "\n")

    # Console output
    mode_prefix = "[TEST] " if mode_manager.is_test_mode else ""
    print(f"{mode_prefix}[{level}] {stage}.{block}: {msg}")


def setup_logging(log_level: str = "INFO"):
    """
    Initialize logging system.
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    _ensure_base_structure()

    logging.basicConfig(
        level=LOG_LEVELS.get(log_level.upper(), logging.INFO),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    mode_manager = get_mode_manager()
    log_event(
        "system",
        "logger",
        "INFO",
        f"Logging initialized ({mode_manager.mode.value})",
        {"log_level": log_level},
    )


def clear_logs(category: Optional[str] = None):
    """
    Clear log files.

    Args:
        category: Specific category to clear (pipeline/stages/adapters/errors)
                 If None, clears all logs
    """
    base = _get_log_base_dir()

    if category:
        d = base / category
        if d.exists():
            for f in d.glob("*.jsonl"):
                f.unlink()
            log_event("system", "logger", "INFO", f"Cleared logs: {category}")
    else:
        # Clear all categories
        for folder in ("pipeline", "stages", "adapters", "errors"):
            d = base / folder
            if d.exists():
                for f in d.glob("*.jsonl"):
                    f.unlink()
        log_event("system", "logger", "INFO", "Cleared all logs")


def get_log_files() -> Dict[str, list]:
    """
    Get list of all existing log files organized by category.

    Returns:
        Dict with categories as keys and lists of file paths as values

    Example:
        {
            'adapters': ['price_internal_001_adapter.jsonl', 'news_internal_001_adapter.jsonl'],
            'stages': ['data_collection.jsonl', 'nan_processing.jsonl'],
            'errors': ['current.jsonl'],
            'pipeline': ['current.jsonl']
        }
    """
    base = _get_log_base_dir()
    result = {}

    for category in ("pipeline", "stages", "adapters", "errors"):
        d = base / category
        if d.exists():
            result[category] = [str(f.name) for f in d.glob("*.jsonl")]
        else:
            result[category] = []

    return result


def get_adapter_logs(adapter_id: str) -> list:
    """
    Get all log entries for a specific adapter.

    Args:
        adapter_id: Adapter ID from config (e.g., 'price_internal_001')

    Returns:
        List of log entries (dicts)
    """
    base = _get_log_base_dir()
    adapter_file = base / "adapters" / f"{adapter_id}_adapter.jsonl"

    if not adapter_file.exists():
        return []

    logs = []
    with open(adapter_file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                logs.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return logs


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("Dynamic Logging Demo (Config-Based)")
    print("=" * 60)

    # Initialize logging
    setup_logging("INFO")

    # Simulate adapter logs from config
    print("\n📊 Simulating logs from data_farm_config.yml adapters:")

    # Adapter 1: price_internal_001
    log_event(
        "data_collection",
        "price_internal_001_adapter",
        "INFO",
        "Fetching data for BINANCE:BTCUSDT.P",
        {"symbol": "BINANCE:BTCUSDT.P", "records": 100},
    )

    # Adapter 2: news_internal_001
    log_event(
        "data_collection",
        "news_internal_001_adapter",
        "INFO",
        "Fetching news",
        {"limit": 100},
    )

    # Adapter 3: fundamental_fmp_001
    log_event(
        "data_collection",
        "fundamental_fmp_001_adapter",
        "INFO",
        "Fetching fundamentals",
        {"cadence": "daily"},
    )

    # Stage logs
    log_event("nan_processing", "cleaner", "INFO", "Cleaned 5 NaN values")
    log_event(
        "data_export", "exporter", "INFO", "Exported BINANCE_BTCUSDT_P/price.parquet"
    )

    # Error log
    log_event(
        "data_collection",
        "price_internal_001_adapter",
        "ERROR",
        "API timeout",
        {"retry_count": 3},
    )

    print("\n" + "=" * 60)
    print("📁 Log Files Created (Dynamic):")
    print("=" * 60)

    for category, files in get_log_files().items():
        if files:
            print(f"\n  {category}/:")
            for f in files:
                print(f"    ✅ {f}")

    print("\n" + "=" * 60)
    print("🔍 Reading Adapter Logs:")
    print("=" * 60)

    logs = get_adapter_logs("price_internal_001")
    print(f"\n  price_internal_001_adapter.jsonl ({len(logs)} entries):")
    for log in logs:
        print(f"    [{log['level']}] {log['message']}")
