"""
Application Mode Manager
Manages TEST vs NORMAL mode for isolated environments
"""

import os
from enum import Enum
from pathlib import Path
from typing import Dict


class AppMode(Enum):
    """Application modes"""

    NORMAL = "normal"
    TEST = "test"


class ModeManager:
    """Manages application mode and environment-specific settings"""

    _instance = None
    _current_mode: AppMode = AppMode.NORMAL
    _initial_mode: AppMode = AppMode.NORMAL

    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize mode manager"""
        # Check environment variable
        env_mode = os.getenv("MARKETPILOT_MODE", "normal").lower()
        if env_mode == "test":
            self._current_mode = AppMode.TEST
            self._initial_mode = AppMode.TEST
        else:
            self._current_mode = AppMode.NORMAL
            self._initial_mode = AppMode.NORMAL

    @property
    def mode(self) -> AppMode:
        """Get current mode"""
        return self._current_mode

    @property
    def is_test_mode(self) -> bool:
        """Check if in test mode"""
        return self._current_mode == AppMode.TEST

    @property
    def is_normal_mode(self) -> bool:
        """Check if in normal mode"""
        return self._current_mode == AppMode.NORMAL

    def set_test_mode(self):
        """Switch to test mode"""
        self._current_mode = AppMode.TEST
        os.environ["MARKETPILOT_MODE"] = "test"

    def set_normal_mode(self):
        """Switch to normal mode"""
        self._current_mode = AppMode.NORMAL
        os.environ["MARKETPILOT_MODE"] = "normal"

    def reset_mode(self):
        """Reset to initial/default mode (usually NORMAL)"""
        self._current_mode = self._initial_mode
        os.environ["MARKETPILOT_MODE"] = self._initial_mode.value

    def get_log_dir(self) -> Path:
        """Get log directory based on mode"""
        if self.is_test_mode:
            return Path("logs_test")
        return Path("logs")

    def get_data_dir(self) -> Path:
        """Get data directory based on mode"""
        if self.is_test_mode:
            return Path("data_test")
        return Path("data")

    def cleanup_test_data(self):
        """Clean up test data (only in test mode)"""
        if not self.is_test_mode:
            raise RuntimeError("Cannot cleanup test data in normal mode!")

        import shutil

        # Remove test directories
        for path in [self.get_log_dir(), self.get_data_dir()]:
            if path.exists():
                shutil.rmtree(path)

    def __repr__(self) -> str:
        return f"ModeManager(mode={self.mode.value})"


# Global instance
mode_manager = ModeManager()


def get_mode_manager() -> ModeManager:
    """Get global mode manager instance"""
    return mode_manager


def is_test_mode() -> bool:
    """Quick check if in test mode"""
    return mode_manager.is_test_mode


def set_test_mode():
    """Quick set test mode"""
    mode_manager.set_test_mode()


def set_normal_mode():
    """Quick set normal mode"""
    mode_manager.set_normal_mode()


def reset_mode():
    """Reset to initial/default mode"""
    mode_manager.reset_mode()


# Example usage
if __name__ == "__main__":
    manager = get_mode_manager()

    print(f"Current mode: {manager.mode.value}")
    print(f"Is test mode: {manager.is_test_mode}")
    print(f"Log directory: {manager.get_log_dir()}")
    print(f"Data directory: {manager.get_data_dir()}")
    print()

    # Switch to test mode
    print("Switching to test mode...")
    set_test_mode()

    print(f"Current mode: {manager.mode.value}")
    print(f"Log directory: {manager.get_log_dir()}")
    print(f"Data directory: {manager.get_data_dir()}")
    print()

    # Reset to initial mode
    print("Resetting to initial mode...")
    reset_mode()

    print(f"Current mode: {manager.mode.value}")
    print(f"Log directory: {manager.get_log_dir()}")
    print()
