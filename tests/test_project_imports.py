from quant_brain.config import BRAIN_DIR, DEFAULT_SYMBOLS


def test_project_paths_exist():
    assert BRAIN_DIR.exists()


def test_default_symbols():
    assert DEFAULT_SYMBOLS == ["SPY", "QQQ", "IWM"]
