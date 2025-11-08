"""
Centralized Logging System for Data Farm
Writes structured JSON lines to organized log directories
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Log directories
LOG_BASE = Path("logs")
LOG_DIRS = {
    "pipeline": LOG_BASE / "pipeline",
    "stages": LOG_BASE / "stages",
    "adapters": LOG_BASE / "adapters",
    "errors": LOG_BASE / "errors",
}

# Log level mapping
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def _create_log_dirs():
    """Create log directories if they don't exist"""
    for dir_path in LOG_DIRS.values():
        dir_path.mkdir(parents=True, exist_ok=True)


def _get_log_file(category: str, stage: str = "") -> Path:
    """Get log file path for a category"""
    log_dir = LOG_DIRS.get(category, LOG_DIRS["pipeline"])

    # For initialization stage in pipeline, use 'current.jsonl' (MP-005 requirement)
    if category == "pipeline" and stage == "initialization":
        return log_dir / "current.jsonl"

    # For all other logs, use timestamped files
    timestamp = datetime.now().strftime("%Y%m%d")
    return log_dir / f"{category}_{timestamp}.jsonl"


def log_event(
    stage: str,
    block: str,
    level: str = "INFO",
    msg: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log an event in JSONL format

    Args:
        stage: Pipeline stage (e.g., 'ingestion', 'quality')
        block: Component block (e.g., 'alphavantage_adapter', 'price_validator')
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        msg: Log message
        extra: Additional fields to include in log

    Example:
        log_event('ingestion', 'fmp_adapter', 'INFO', 'Fetched 100 records', {'symbol': 'AAPL'})
    """
    # Create directories if needed
    _create_log_dirs()
    if stage == "initialization":
        category = "pipeline"
    # THEN: Check other conditions
    elif level in ["ERROR", "CRITICAL"]:
        category = "errors"
    elif "adapter" in block.lower():
        category = "adapters"
    elif "stage" in block.lower() or stage.lower() in [
        "ingestion",
        "quality",
        "storage",
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

    # Add extra fields
    if extra:
        log_entry.update(extra)

    # Write to JSONL file
    log_file = _get_log_file(category, stage)  # Pass stage here
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

    # Also print to console for development
    print(f"[{level}] {stage}.{block}: {msg}")


def setup_logging(log_level: str = "INFO"):
    """
    Initialize logging system

    Args:
        log_level: Minimum log level to capture (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    _create_log_dirs()

    # Configure Python's logging module
    logging.basicConfig(
        level=LOG_LEVELS.get(log_level.upper(), logging.INFO),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    log_event(
        "system",
        "logger",
        "INFO",
        "Logging system initialized",
        {"log_level": log_level},
    )


# Example usage and tests
if __name__ == "__main__":
    # Initialize logging
    setup_logging("DEBUG")
