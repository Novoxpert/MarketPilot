"""
Run script for ResilientDataFarm
Entry point to execute the data pipeline
"""

from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
from data_farm.resilient_data_farm import ResilientDataFarm
from data_farm.utils.logger import log_event


def main():
    """Main execution function"""
    try:
        log_event(
            stage="pipeline",
            block="run_script",
            level="INFO",
            msg="Starting Data Farm pipeline",
        )

        # Initialize Data Farm
        farm = ResilientDataFarm(config_path="data_farm/config/data_farm_config.yaml")
        # Log success
        log_event(
            stage="pipeline",
            block="run_script",
            level="INFO",
            msg="Initialization Complete",
            extra={
                "adapters_count": len(farm.get_adapters()),
                "status": "ready",
            },
        )

        print("\n✅ Data Farm initialized successfully!")
        print(f"📊 Loaded {len(farm.get_adapters())} adapter(s)")
        print("📝 Check logs/pipeline/ for detailed logs")

    except Exception as e:
        log_event(
            stage="pipeline",
            block="run_script",
            level="ERROR",
            msg=f"Failed to initialize Data Farm: {str(e)}",
        )
        print(f"\n❌ Initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
