import json
from dataclasses import replace

from vpn_counter.settings import Settings


def test_settings_roundtrip(tmp_path):
    path = tmp_path / "settings.json"
    settings = replace(Settings(), model="turbo", last_count=27, overlay_color="#ffffff")
    settings.save(path)
    assert Settings.load(path) == settings


def test_invalid_settings_recover_without_crashing(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("broken json", encoding="utf-8")
    assert Settings.load(path) == Settings()
    path.write_text(
        json.dumps({"model": "unknown", "last_count": -4, "overlay_size": 10000}),
        encoding="utf-8",
    )
    settings = Settings.load(path)
    assert settings.model == "large-v3"
    assert settings.last_count == 0
    assert settings.overlay_size == 80
