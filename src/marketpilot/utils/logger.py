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


def _get_log_base_dir() -> Path:
    """Get base log directory based on mode"""
    return get_mode_manager().get_log_dir()


def _create_log_dirs():
    """Create log directories if they don't exist"""
    log_base = _get_log_base_dir()

    log_dirs = {
        "pipeline": log_base / "pipeline",
        "stages": log_base / "stages",
        "adapters": log_base / "adapters",
        "errors": log_base / "errors",
    }

    for dir_path in log_dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)

    return log_dirs


def _get_log_file(category: str, stage: str = "", level: str = "INFO") -> Path:
    """
    Get log file path

    Args:
        category: Log category (pipeline, stages, adapters, errors)
        stage: Stage name (for special handling)
        level: Log level

    Returns:
        Path to log file
    """
    log_base = _get_log_base_dir()
    log_dir = log_base / category

    # Add mode prefix in test mode
    # mode_manager = get_mode_manager()
    # prefix = "test_" if mode_manager.is_test_mode else ""

    if category == "errors":
        return log_dir / "current.jsonl"

    elif category == "pipeline":
        if stage == "initialization":
            return log_dir / "initialization.jsonl"
        return log_dir / "pipeline.jsonl"

    elif category == "stages":
        # Each stage gets its own file
        # if stage:
        #     return log_dir / "{stage}.jsonl"
        return log_dir / "stages.jsonl"

    elif category == "adapters":
        return log_dir / "adapters.jsonl"

    else:
        return log_dir / f"{category}.jsonl"


def log_event(
    stage: str,
    block: str,
    level: str = "INFO",
    msg: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log an event in JSONL format (mode-aware)

    Args:
        stage: Pipeline stage (e.g., 'ingestion', 'quality')
        block: Component block (e.g., 'alphavantage_adapter', 'price_validator')
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        msg: Log message
        extra: Additional fields to include in log
    """
    # Create directories if needed
    _create_log_dirs()

    # Determine category based on level and block
    if stage == "initialization":
        category = "pipeline"
    elif level in ["ERROR", "CRITICAL"]:
        category = "errors"
    elif "adapter" in block.lower():
        category = "adapters"
    elif "stage" in block.lower() or stage.lower() in [
        "ingestion",
        "quality",
        "storage",
        "health_check",
        "data_collection",
        "nan_processing",
        "temporal_alignment",
        "deduplication",
        "quality_assurance",
        "data_export",
    ]:
        category = "stages"
    else:
        category = "pipeline"

    # Build log entry
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "stage": stage,
        "block": block,
        "level": level,
        "message": msg,
    }

    # Add mode info in test mode
    mode_manager = get_mode_manager()
    if mode_manager.is_test_mode:
        log_entry["test_mode"] = True

    # Add extra fields
    if extra:
        log_entry.update(extra)

    # Write to JSONL file (append mode)
    log_file = _get_log_file(category, stage, level)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

    # Also print to console for development (with mode indicator)
    mode_prefix = "[TEST] " if mode_manager.is_test_mode else ""
    print(f"{mode_prefix}[{level}] {stage}.{block}: {msg}")


def setup_logging(log_level: str = "INFO"):
    """
    Initialize logging system (mode-aware)

    Args:
        log_level: Minimum log level to capture
    """
    _create_log_dirs()

    # Configure Python's logging module
    logging.basicConfig(
        level=LOG_LEVELS.get(log_level.upper(), logging.INFO),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    mode_manager = get_mode_manager()
    log_event(
        "system",
        "logger",
        "INFO",
        f"Logging system initialized in {mode_manager.mode.value} mode",
        {"log_level": log_level, "mode": mode_manager.mode.value},
    )


def clear_logs(category: Optional[str] = None):
    """
    Clear log files (useful for testing)

    Args:
        category: Specific category to clear, or None for all
    """
    log_base = _get_log_base_dir()

    if category:
        # Clear specific category
        category_dir = log_base / category
        if category_dir.exists():
            for log_file in category_dir.glob("*.jsonl"):
                log_file.unlink()
    else:
        # Clear all logs
        for category in ["pipeline", "stages", "adapters", "errors"]:
            category_dir = log_base / category
            if category_dir.exists():
                for log_file in category_dir.glob("*.jsonl"):
                    log_file.unlink()


# Example usage
if __name__ == "__main__":
    from marketpilot.utils.mode_manager import set_test_mode

    print("=" * 60)
    print("Normal Mode Logging")
    print("=" * 60)

    setup_logging("INFO")
    log_event("test", "test_block", "INFO", "Normal mode log")

    print()
    print("=" * 60)
    print("Test Mode Logging")
    print("=" * 60)

    set_test_mode()
    setup_logging("INFO")
    log_event("test", "test_block", "INFO", "Test mode log")

    print()
    print("Log files created:")
    print("  logs/pipeline/pipeline.jsonl")
    print("  logs/stages/stages.jsonl")
    print("  logs/adapters/adapters.jsonl")
    print("  logs/errors/errors.jsonl")
    print()
    print("Test mode:")
    print("  logs_test/pipeline/test_pipeline.jsonl")
    print("  logs_test/stages/test_stages.jsonl")
    print("  etc.")
