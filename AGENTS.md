# VPNCounter

Native Windows desktop application. Use Python 3.12, PySide6 widgets, sounddevice,
and faster-whisper. Recognition defaults to Hungarian, Whisper large-v3, CUDA,
and FP16. The control panel and presentation overlay share one counter state.

- Follow the repository preferences in the parent `AGENTS.md`.
- Work and commit locally on `main`; GitHub access stays read-only.
- Install with `uv sync --extra gpu`; run with `uv run --extra gpu vpn-counter`.
- Check with `uv run --extra gpu pytest` and `uv run --extra gpu ruff check .`.
- Keep recognition off the Qt GUI thread and microphone callbacks lightweight.
- Count Hungarian VPN inflections, compounds, and spelled letter names.
- Deduplicate overlapping audio by timestamps; preserve repeated mentions in one sentence.
- Keep microphone capture opt-in. Store settings locally, and audio only in memory.
- Models and GPU runtime files belong outside version control.
- Put project documentation in `docs/`; keep launch instructions in `README.md`.
