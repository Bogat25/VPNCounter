# VPN Counter

A local Windows app that counts spoken mentions of **VPN** during a Hungarian
presentation. A small counter floats over the PowerPoint slideshow, while a
separate control panel stays on the presenter's screen.

Default recognition: **Whisper large-v3 · NVIDIA CUDA · FP16 · Hungarian**.

## Run on this computer

Double-click **`Start VPN Counter.cmd`**, or run:

```powershell
.\scripts\run.ps1
```

Choose a microphone and the presentation display, then click **Start listening**.
Unlock the overlay to drag it into place; lock it before starting the slideshow.
Under **Presentation overlay → Position**, choose **Top left**, **Top right**,
**Bottom left**, or **Bottom right**. Corners stay anchored as the count and
overlay size change. **Custom (drag)** unlocks manual positioning.
The microphone is opened only after the model is ready and you start a session.
Pause stops the microphone stream. Ending a session keeps the displayed count.

The **V icon in the Windows tray** (beside the clock, possibly inside the `^`
hidden-icons menu) reopens the control panel with a click. Right-click it for
listening controls, overlay visibility, or **Exit VPN Counter**. Closing the
control panel or clicking **Hide to tray** keeps the counter running. Use
**Exit VPN Counter** from the tray menu to stop the application.

The first session downloads the public model to
`%LOCALAPPDATA%\VPNCounter\models\large-v3`. The control panel shows a download
percentage, followed by separate loading and warmup messages. Once cached,
recognition works offline.
No API key is needed. Audio is kept in a bounded memory buffer; it is not saved
or uploaded. Settings and the last counter value are stored locally.

The app stays portable. Click **Storage & cleanup** in the Recognition panel to
open the data folder or remove downloaded models. **Clean up and exit** stops
recognition before removing files; **Also remove settings and saved counter**
is optional. Models are selected by default. Removed models download again on
the next listening session. Normal exits and app updates keep your cached models.
To remove everything, select both cleanup options, let the app exit, then delete
its portable folder. Deleting the portable folder alone leaves the cached data.

## Set up another computer

Install Python 3.12 and [uv](https://docs.astral.sh/uv/), then run:

```powershell
.\scripts\setup.ps1
```

The script also supports Python's `pip` if uv is unavailable. The GPU installation
includes CUDA 12 cuBLAS and cuDNN 9 libraries inside the app's virtual environment;
an up-to-date NVIDIA driver is still required. It does not replace the system CUDA
installation. CPU-only installation: `scripts/setup.ps1 -CpuOnly`, then choose
**Small** and **CPU** in the application.

## What counts

- `VPN`, `VPN-t`, `VPN-en`, `VPN-ek`, `VPN-es`, directly attached endings, and
  compounds such as `VPN-kapcsolat`.
- Separated letters: `V P N`, `V.P.N.`, `V-P-N`.
- Hungarian letter names: `vé pé en`, `vé-pé-en`, `vépéen`, including endings.
- English letter names rendered as Hungarian text: `ví pí en`.
- Common product compounds: `OpenVPN`, `NordVPN`, `ProtonVPN`, `ExpressVPN`.

Every separate mention counts. `VPN, VPN` adds two. Overlapping recognition
windows are matched by timestamps so repeated observations do not add duplicates.
Words such as `titkosítás` and `magánhálózat` alone do not increment the counter.

Word confidence is a model score, not a calibrated accuracy guarantee. Raising
the minimum match confidence rejects more uncertain detections. Every recognized
word in a spelled acronym must meet that threshold. Recognition uses ordinary Hungarian
transcription without a VPN keyword hint, which could bias unclear speech toward
the target word. Microphone quality and pronunciation affect results: rehearse
with the actual presenters
and presentation microphone before the event.

## Presentation controls

| Shortcut | Action |
|---|---|
| Ctrl+Alt+P | Start, pause, or resume |
| Ctrl+Alt+Up | Add one |
| Ctrl+Alt+Down | Subtract one |
| Ctrl+Alt+R | Reset |
| Ctrl+Alt+O | Show or hide the overlay |

Shortcuts work while PowerPoint has focus. If another program owns a shortcut,
the control panel reports the conflict. Manual correction does not cause the
same previously detected audio to be counted again.

Use **Display** to place the overlay on the projector rather than Presenter View.
For a remote presentation, share the entire presentation display; sharing only
the PowerPoint window may omit the separate overlay. Test full-screen slideshow
visibility and slide controls on the actual presentation setup.

## Windows executable

Exit any running copy from the tray before rebuilding its folder. The build
script checks this before replacing files.

```powershell
.\scripts\build.ps1
```

Run `dist\VPNCounter\VPNCounter.exe`. Keep the entire `dist\VPNCounter` folder
together: it includes Python, Qt, audio libraries, and NVIDIA runtime libraries.
Model files remain in the local application-data folder and are downloaded on
first use on another machine. The executable does not require a separate Python
installation on the destination computer.

## Development and checks

Automatic Windows downloads for version tags are configured in
[.github/workflows/release.yml](.github/workflows/release.yml).
See [docs/releases.md](docs/releases.md) for versioning and release instructions.

```powershell
uv sync --extra gpu
uv run --extra gpu vpn-counter
uv run --extra gpu pytest -q
uv run --extra gpu ruff check .
uv run --extra gpu python scripts/preview.py
```

Keep `--extra gpu` in uv commands so uv retains the optional GPU dependencies.

Benchmark an existing rehearsal recording using the same overlapping windows:

```powershell
.venv\Scripts\python.exe scripts/benchmark.py rehearsal.wav --expected 12
```

The report contains the count, timestamps, model confidence, and processing time.
Compare `--model turbo` with `--model large-v3` if you need faster updates.
Use `--output artifacts/rehearsal.json` to keep the report. An expected-count
mismatch returns a nonzero exit code.

Check GPU inference, VAD, audio-device enumeration, and packaged libraries
without opening the microphone:

```powershell
.\dist\VPNCounter\VPNCounter.exe --diagnose artifacts/runtime.json
```

The report sets `ok` to `true` on success. This uses the default large-v3 model
and downloads it if it has not been cached yet.

Architecture: [docs/architecture.md](docs/architecture.md).
Verification notes: [docs/validation.md](docs/validation.md).
