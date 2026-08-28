from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BRAIN_DIR = PROJECT_ROOT / "brain"
DATA_DIR = PROJECT_ROOT / "data"
DB_DIR = PROJECT_ROOT / "db"
REPORTS_DIR = PROJECT_ROOT / "reports"

DEFAULT_SYMBOLS = ["SPY", "QQQ", "IWM"]
DEFAULT_TIMEFRAME = "1d"
