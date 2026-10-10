# Verification

Checked on 2026-10-08 through 2026-10-10 on Windows 11, Python 3.12.10, and an NVIDIA GeForce
RTX 5060 Laptop GPU with 8151 MiB VRAM. Current source and packaged UI checks
are for version 0.1.4. The initial hardware checks below used full Whisper
large-v3, CUDA FP16, Hungarian, beam size 5, and minimum match confidence 0.45;
they predate the removal of the VPN keyword hint.

## Automated checks

- `pytest -q`: **90 passed**. Coverage includes Hungarian VPN forms, confidence
  filtering, overlapping-window duplicates, rapid repeated mentions, bounded
  audio history, overflow/reset invalidation, validated settings, shared UI and
  overlay state, manual corrections, rejection of stale queued results, tray
  restoration and explicit exit, four corner anchors, settings migration, and
  versioned release packaging, cleanup selection and cancellation, worker stop
  ordering, preservation of settings, cleanup error recovery, safe handling of
  Windows junctions, and process-local download cache locations. New cases cover
  neutral decoding, invalid word timings, weak letters in spelled acronyms,
  tag-derived versions, byte percentages, cached files, transfer retries, Xet
  network/reconstruction updates, and late progress during shutdown. Release
  checks cover both download formats, missing standalone builds, checksum
  tampering, asset size limits, custom build paths, and CLI packaging/verification.
- `ruff check .` and `ruff format --check .`: passed.
- The real widgets were rendered and visually inspected. Preview images are
  generated locally in `artifacts/` using `scripts/preview.py`.

## Initial GPU speech check

Two synthetic Hungarian clips were generated locally with Piper 1.8.0 and
`hu_HU-anna-medium`. The source text is in `tests/fixtures/`. No presenter audio
was used. The benchmark follows the live six-second overlapping windows,
two-second hop, and trailing word guard, then flushes the final partial window.

| Clip | Duration | Expected | Counted | Processing | Slowest window |
|---|---:|---:|---:|---:|---:|
| Hungarian VPN mentions and suffixes | 18.03 s | 4 | 4 | 10.85 s | 1.48 s |
| Hungarian network speech without VPN | 17.62 s | 0 | 0 | 10.85 s | 1.90 s |

Processing excludes model loading and warmup. These clips establish that the
initial installed pipeline worked; they do not validate the current recognition
change or measure accuracy for human presenters,
accents, background noise, or all VPN product names. Model confidence is not
an accuracy percentage. Timing varies with other applications and GPU load.

To reproduce the clips and reports, run from the repository root:

```powershell
uv tool run --from piper-tts==1.8.0 --python 3.12 python -m piper.download_voices hu_HU-anna-medium --data-dir .cache/voices
uv tool run --from piper-tts==1.8.0 --python 3.12 piper -m hu_HU-anna-medium --data-dir .cache/voices --input-file tests/fixtures/hungarian-positive.txt -f .cache/positive.wav --sentence-silence 0.6
uv tool run --from piper-tts==1.8.0 --python 3.12 piper -m hu_HU-anna-medium --data-dir .cache/voices --input-file tests/fixtures/hungarian-negative.txt -f .cache/negative.wav --sentence-silence 0.6
.venv\Scripts\python.exe scripts/benchmark.py .cache/positive.wav --expected 4 --output artifacts/positive.json
.venv\Scripts\python.exe scripts/benchmark.py .cache/negative.wav --expected 0 --output artifacts/negative.json
```

The public voice is downloaded on first use. Piper is a separate development
tool; it is not included in the application or its dependencies.

## Recognition and download update

- Removed the VPN-only decoding hint, enabled silence-hallucination suppression,
  rejected non-finite/zero-duration word data, and made confidence filtering use
  the weakest recognized word in a spelled acronym. Unit regressions include
  ordinary Hungarian speech, an uncertain hallucinated segment, and weak letters.
- Added `hungarian-everyday-negative.txt` with everyday phrases including
  `végén`, `gépen`, and `szépen`. The synthetic clip was generated locally, but
  the 0.1.2 GPU recognition checks could not complete: the full large-v3 weights
  were absent and both download attempts stalled. The initial GPU results above
  remain a historical baseline. Current false-positive rates still need a
  known-count passage with the real presenters and microphone.
- A real public tokenizer download through the installed Hub client produced
  byte progress through 0%, 99%, and 100%. Automated cases cover cached files,
  initial/resumed byte counts, retries, failed downloads without false 100%,
  and Xet's separate network/reconstruction reports without double counting.
- The rebuilt 0.1.2 executable passed its frozen smoke check with
  `download_progress_ok: true` and `storage_dialog_ok: true`, without opening
  the microphone or loading a model. The 42% state was rendered and inspected
  in `artifacts/model-download.png`.
- Local packaging produced a refreshed 0.1.2 portable ZIP. Its CRC, SHA-256,
  version manifest, bundled speech/GPU dependencies, and executable match were
  verified. The default `dist` copy was left running; the updated executable
  is in `artifacts/builds/v0.1.2/VPNCounter/`.

## Windows integration

- The Realtek WASAPI microphone opened on the background recognition thread at
  its native 48 kHz. Audio reached the memory buffer, pause stopped capture and
  cleared the buffer, and resume captured new samples. No recording was saved.
- Windows COM initialization on the audio thread is required for this device's
  callback stream. This was checked against the actual hardware after adding
  balanced initialization and cleanup.
- The PyInstaller folder distribution launched a native control panel and
  overlay. Windows window styles confirmed that the overlay was topmost,
  transparent to clicks, and unable to activate itself.
- A Windows `WM_HOTKEY` message exercised the registered native event handler,
  incremented the count, and persisted the correct value on normal exit. The
  original settings were restored after the check. Physical shortcut presses
  during a slideshow still need rehearsal.
- The packaged runtime diagnostic loaded large-v3 from the local cache and
  completed CUDA inference and Silero VAD without a microphone. It discovered
  its own bundled cuBLAS, cuDNN, and NVRTC libraries, and returned `ok: true`.
- PyAV is constrained below version 17 because the initially resolved version
  19 rejected an argument used by faster-whisper's audio decoder. Version
  16.1.0 passed file decoding and packaged runtime checks.

Local runtime, GUI, speech reports, generated audio, models, and build output
are excluded from Git. The reproducible source and dependency lock are committed.

## Tray, positioning, and release checks

- A native Windows Qt run confirmed that the V icon was registered in the tray,
  closing the control panel left the overlay running, tray activation restored
  the panel, and Exit removed both the tray icon and overlay. No microphone or
  model was opened during this check.
- All four corner presets were checked against a display with a negative global
  origin, then checked again after changing font size and growing the counter
  to five digits. A native Windows bottom-right check also passed. A manually
  dragged position switches to Custom and survives resizing.
- The source and rebuilt executable passed `--smoke-test`, including rendering
  both windows and importing the frozen speech dependencies without loading a
  model or capturing audio.
- Actionlint 1.7.12 accepted `.github/workflows/release.yml`. The dependency
  lock is current. The workflow prepares the app version from a stable release
  tag before dependency installation. Tests verify that preparation updates
  only app version entries, preserves dependency pins, rejects malformed tags
  and metadata, and supports a tag newer than the source's recorded version.
  The local `v0.1.2` preparation passed locked dependency installation.
- Local packaging produced a ZIP of about 1.44 GiB containing
  500 files. The executable, cuBLAS, cuDNN, VAD assets, launch instructions, and
  version manifest were present. Every ZIP CRC and the SHA-256 checksum passed.
- The GitHub-hosted build and publication were not run. No tags, commits, or
  releases were published remotely. A new version tag on the fixed commit must
  be published by the user to exercise the hosted workflow; rerunning an older
  failed tag continues to use that tag's old workflow.

## Portable cleanup

- The native Windows app was exercised through its Storage & cleanup button,
  using temporary app-data folders. The real model cache was kept untouched.
- With default selections, cleanup removed models, saved the current counter,
  kept settings, removed the instance lock, and exited. Selecting settings as
  well removed both data categories and the empty app-data directory. The tray
  was available during both runs. Neither run loaded a model or opened the mic.
- Automated tests also checked cancellation, waiting for recognition to finish,
  retry after a file error, preservation of unrelated files, and root/nested
  Windows junction behavior against disposable fixtures.
- The rebuilt executable passed its smoke check, including rendering the
  storage dialog and verifying the default selections. The portable ZIP was
  refreshed with the new executable and cleanup instructions.
- Large-v3 CUDA inference and Silero VAD still passed against the existing
  cache after configuring process-local downloader cache paths. No microphone
  was opened by that diagnostic.

## Standalone portable release

- Version 0.1.4 builds both the folder app and a standalone EXE from the same
  PyInstaller analysis. Both passed their frozen UI/speech import checks, with
  the correct version, without opening a microphone or loading a model.
- The standalone executable is about 1.44 GiB. Its embedded archive contains
  Python, Qt, cuBLAS, cuDNN, Silero VAD, and the Xet download extension. The
  archive reader found 510 entries totaling about 2.37 GiB before extraction.
- The standalone smoke run used a working directory without `_internal` and
  an isolated temporary directory. Its extraction was observed and the
  temporary files were removed on normal exit. The complete extraction, UI
  check, and exit took 28.6 seconds on this computer. Normal startup time varies.
- Release packaging preserves the folder ZIP and adds the versioned standalone
  EXE with checksums for both. Both hashes, ZIP CRCs, version metadata, and
  matches with the tested build files were verified locally. The workflow checks both packaged formats and
  verifies both assets before publication. Actionlint and PowerShell syntax
  checks passed. GitHub publication was not run locally.

## Changing recognition settings during a session

Checked on 2026-10-10:

- `uv run --extra gpu pytest`: **111 passed**. The regression cases cover model,
  CPU/GPU, and microphone changes during loading, listening, and pause; rapid
  changes; cancellation by End, exit, and cleanup; microphone refresh and
  removal; rejection of retired worker signals; and preservation of the counter,
  saved settings, and cached models. Confidence changes apply without restarting.
- `uv run --extra gpu ruff check .`: passed.
- A real Qt background thread with a simulated model loader and audio loop
  confirmed that replacement waits for the previous load to finish, applies the
  latest model choice, and keeps the GUI responsive. Both loads ran off the GUI
  thread. These checks did not load Whisper weights or open a microphone.
- Recognition controls remain editable while the previous operation finishes.
  Active listening restarts with the latest choices; changing settings while
  paused waits for Start listening. Cleanup is not needed.
- Rebuilt both Windows distributions with `scripts/build.ps1`. The folder app
  and standalone EXE both passed `--smoke-test`, including frozen speech imports,
  UI rendering, the storage dialog, and download progress. Neither check opened
  a microphone or loaded a model. Switching actual Whisper models and physical
  microphones still needs a manual session.

## Portable update and model dropdown regression

Checked on 2026-10-10 after a report that model selection was still disabled:

- The running downloaded v0.1.5 executable contained the old UI code, including
  setup locking when starting recognition. Its bundled module lacked the settings
  change handler present in the fixed local build. Downloading or building a new
  EXE does not replace a copy already running in the tray.
- Added mouse and keyboard input checks against the model dropdown while loading,
  listening, and paused. All three passed against both the source module and the
  UI bytecode extracted directly from the fixed standalone EXE. Simulated workers
  kept these checks independent of downloaded models and microphone hardware.
- `uv run --extra gpu pytest`: **114 passed**; `ruff check .` and
  `ruff format --check .`: passed. Corrected test formatting required by the
  release workflow, which was missed during the earlier local verification.
- Prepared a clearly named local copy of the fixed standalone EXE and verified
  that its SHA-256 matches the tested build. Updating requires exiting the old
  tray process and opening the fixed copy; settings and models need no cleanup.
- Opened the fixed copy after the old process exited and confirmed that its
  native control panel was running from the updated executable.

## Rehearsal still needed

Run the app with the actual presenters and microphone. Check a known-count
passage, Hungarian suffixes, repeated VPN mentions, silence, and background
speech. Use manual correction or adjust confidence if needed. Test overlay
visibility and slide navigation in PowerPoint's full-screen slideshow on the
presentation display. For remote presentations, share that entire display.
Turbo/GPU and Small/CPU are available but were not benchmarked in this check.
