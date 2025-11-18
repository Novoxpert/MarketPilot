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
    base = _get_log_base_dir()

    dirs = {
        "pipeline": base / "pipeline",
        "stages": base / "stages",
        "adapters": base / "adapters",
        "errors": base / "errors",
    }

    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    # Create pipeline/default file
    (dirs["pipeline"] / "current.jsonl").touch(exist_ok=True)

    # Predefined STAGES
    stage_names = [
        "health_check",
        "data_collection",
        "nan_processing",
        "temporal_alignment",
        "deduplication",
        "quality_assurance",
        "data_export",
    ]
    for s in stage_names:
        (dirs["stages"] / f"{s}.jsonl").touch(exist_ok=True)

    # Predefined ADAPTERS
    adapter_names = [
        "price_yfinance",
        "news_alpha_vantage",
        "fundamental_fmp",
    ]
    for a in adapter_names:
        (dirs["adapters"] / f"{a}.jsonl").touch(exist_ok=True)

    # Error file
    (dirs["errors"] / "current.jsonl").touch(exist_ok=True)

    return dirs


def _resolve_log_file(stage: str, block: str, level: str) -> Path:
    base = _get_log_base_dir()

    # ---- ERRORS ALWAYS GO HERE ----
    if level in ("ERROR", "CRITICAL"):
        return base / "errors" / "current.jsonl"

    # ---- ADAPTERS ----
    if "adapter" in block.lower() or block.endswith("_adapter"):
        adapter_file = base / "adapters" / f"{block}.jsonl"
        return adapter_file

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

    # ---- DEFAULT PIPELINE ----
    return base / "pipeline" / "current.jsonl"


def log_event(
    stage: str,
    block: str,
    level: str = "INFO",
    msg: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    _create_log_dirs()

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

    # Add extra fields
    if extra:
        log_entry.update(extra)

    # Select correct file
    log_file = _resolve_log_file(stage, block, level)

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

    # Console output
    mode_prefix = "[TEST] " if mode_manager.is_test_mode else ""
    print(f"{mode_prefix}[{level}] {stage}.{block}: {msg}")


def setup_logging(log_level: str = "INFO"):
    _create_log_dirs()

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
    base = _get_log_base_dir()

    if category:
        d = base / category
        if d.exists():
            for f in d.glob("*.jsonl"):
                f.unlink()
    else:
        for folder in ("pipeline", "stages", "adapters", "errors"):
            d = base / folder
            if d.exists():
                for f in d.glob("*.jsonl"):
                    f.unlink()


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
    print("  logs/pipeline/current.jsonl")
    print("  logs/stages/*.jsonl")
    print("  logs/adapters/*.jsonl")
    print("  logs/errors/current.jsonl")
    print()
    print("Test mode:")
    print("  logs_test/pipeline/current.jsonl")
    print("  logs_test/stages/*.jsonl")
    print("  logs_test/adapters/*.jsonl")
    print("  logs_test/errors/current.jsonl")
