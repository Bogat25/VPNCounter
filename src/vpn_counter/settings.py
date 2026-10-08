from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


def data_directory() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    return Path(base) / "VPNCounter" if base else Path.home() / ".local/share/VPNCounter"


@dataclass(frozen=True, slots=True)
class Settings:
    model: str = "large-v3"
    device: str = "cuda"
    microphone: str = ""
    screen: str = ""
    overlay_size: int = 36
    overlay_opacity: int = 92
    overlay_color: str = "#a78bfa"
    overlay_x: int = 24
    overlay_y: int = 24
    overlay_background: bool = True
    confidence: float = 0.45
    last_count: int = 0

    @classmethod
    def load(cls, path: Path | None = None) -> Settings:
        path = path or data_directory() / "settings.json"
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return cls()
            defaults = asdict(cls())
            values = {
                key: raw[key]
                for key, default in defaults.items()
                if key in raw and type(raw[key]) is type(default)
            }
            values["model"] = (
                values.get("model", "large-v3")
                if values.get("model", "large-v3") in {"large-v3", "turbo", "small"}
                else "large-v3"
            )
            values["device"] = "cpu" if values.get("device") == "cpu" else "cuda"
            values["overlay_size"] = max(20, min(80, values.get("overlay_size", 36)))
            values["overlay_opacity"] = max(30, min(100, values.get("overlay_opacity", 92)))
            values["confidence"] = max(0.0, min(1.0, values.get("confidence", 0.45)))
            values["last_count"] = max(0, values.get("last_count", 0))
            color = values.get("overlay_color", "#a78bfa")
            if len(color) != 7 or not color.startswith("#"):
                values["overlay_color"] = "#a78bfa"
            else:
                try:
                    int(color[1:], 16)
                except ValueError:
                    values["overlay_color"] = "#a78bfa"
            return cls(**values)
        except (OSError, ValueError, TypeError):
            return cls()

    def save(self, path: Path | None = None) -> None:
        path = path or data_directory() / "settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
