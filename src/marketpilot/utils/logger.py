"""
Centralized Logging System for Data Farm
Writes structured JSON lines to organized log directories
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# -----------------------------
# Base Directories
# -----------------------------
LOG_BASE = Path("logs")
LOG_DIRS = {
    "pipeline": LOG_BASE / "pipeline",
    "stages": LOG_BASE / "stages",
    "adapters": LOG_BASE / "adapters",
    "errors": LOG_BASE / "errors",
}


# -----------------------------
# Helpers
# -----------------------------
def _create_log_dirs():
    for d in LOG_DIRS.values():
        d.mkdir(parents=True, exist_ok=True)


def _get_log_file(category: str, stage: str) -> Path:
    """
    Rules:
    - initialization → logs/pipeline/current.jsonl   (MP-005 requirement)
    - all others → timestamped daily files
    """
    if stage == "initialization":
        return LOG_DIRS["pipeline"] / "current.jsonl"

    timestamp = datetime.now().strftime("%Y%m%d")
    return LOG_DIRS[category] / f"{category}_{timestamp}.jsonl"


# -----------------------------
# Categorization Logic
# -----------------------------
def _detect_category(stage: str, block: str, level: str) -> str:
    if stage == "initialization":
        return "pipeline"

    if level in ("ERROR", "CRITICAL"):
        return "errors"

    if "adapter" in block.lower():
        return "adapters"

    if stage.lower() in [
        "health_check",
        "data_collection",
        "nan_processing",
        "temporal_alignment",
        "deduplication",
        "quality_assurance",
        "export",
    ]:
        return "stages"

    return "pipeline"


# -----------------------------
# Main Log Event
# -----------------------------
def log_event(
    stage: str,
    block: str,
    level: str = "INFO",
    msg: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    _create_log_dirs()

    category = _detect_category(stage, block, level)
    log_file = _get_log_file(category, stage)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "stage": stage,
        "block": block,
        "level": level,
        "message": msg,
    }

    if extra is not None:
        entry["extra"] = extra

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    print(f"[{level}] {stage}.{block}: {msg}")  # dev mode


# -----------------------------
# Setup
# -----------------------------
def setup_logging(log_level: str = "INFO"):
    _create_log_dirs()

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Must be initialization stage for MP-005
    log_event(
        "initialization",
        "logger",
        "INFO",
        "Logging system initialized",
        {"log_level": log_level},
    )


# For testing
if __name__ == "__main__":
    setup_logging("DEBUG")
