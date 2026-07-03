"""SimpleETL Core — Desktop ETL pipeline implementation."""

__version__ = "0.2.0"

from .config_manager import load_config, save_config
from .etl_pipeline import process_batch, process_pipeline
from .main_ui import SimpleETLApp
