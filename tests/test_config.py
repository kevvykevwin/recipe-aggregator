import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "backend" / "config.py"
SPEC = importlib.util.spec_from_file_location("backend_config", MODULE_PATH)
assert SPEC and SPEC.loader
config = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(config)

Settings = config.Settings


def test_settings_strip_whitespace_from_env_strings(monkeypatch) -> None:
    monkeypatch.setenv("NOTION_TOKEN", "   ")
    monkeypatch.setenv("INSTAGRAM_USERNAME", "  kevvykevwin  ")

    settings = Settings()

    assert settings.notion_token == ""
    assert settings.instagram_username == "kevvykevwin"
