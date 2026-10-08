# Verification

Checked on 2026-10-08 on Windows 11, Python 3.12.10, and an NVIDIA GeForce
RTX 5060 Laptop GPU with 8151 MiB VRAM. Recognition used full Whisper large-v3,
CUDA FP16, Hungarian, beam size 5, and minimum match confidence 0.45.

## Automated checks

- `pytest -q`: **56 passed**. Coverage includes Hungarian VPN forms, confidence
  filtering, overlapping-window duplicates, rapid repeated mentions, bounded
  audio history, overflow/reset invalidation, validated settings, shared UI and
  overlay state, manual corrections, rejection of stale queued results, tray
  restoration and explicit exit, four corner anchors, settings migration, and
  versioned release packaging, cleanup selection and cancellation, worker stop
  ordering, preservation of settings, cleanup error recovery, safe handling of
  Windows junctions, and process-local download cache locations.
- `ruff check .` and `ruff format --check .`: passed.
- The real widgets were rendered and visually inspected. Preview images are
  generated locally in `artifacts/` using `scripts/preview.py`.

## GPU speech check

Two synthetic Hungarian clips were generated locally with Piper 1.8.0 and
`hu_HU-anna-medium`. The source text is in `tests/fixtures/`. No presenter audio
was used. The benchmark follows the live six-second overlapping windows,
two-second hop, and trailing word guard, then flushes the final partial window.

| Clip | Duration | Expected | Counted | Processing | Slowest window |
|---|---:|---:|---:|---:|---:|
| Hungarian VPN mentions and suffixes | 18.03 s | 4 | 4 | 10.85 s | 1.48 s |
| Hungarian network speech without VPN | 17.62 s | 0 | 0 | 10.85 s | 1.90 s |

Processing excludes model loading and warmup. These clips establish that the
installed pipeline works; they do not measure accuracy for human presenters,
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
  lock is current. The local version validator accepted `v0.1.0`; automated
  tests rejected malformed tags and mismatched source versions.
- Local packaging produced a ZIP of about 1.44 GiB containing
  500 files. The executable, cuBLAS, cuDNN, VAD assets, launch instructions, and
  version manifest were present. Every ZIP CRC and the SHA-256 checksum passed.
- The GitHub-hosted build and publication were not run. No tags, commits, or
  releases were published remotely. A matching version tag must be published by
  the user to exercise the hosted workflow.

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

## Rehearsal still needed

Run the app with the actual presenters and microphone. Check a known-count
passage, Hungarian suffixes, repeated VPN mentions, silence, and background
speech. Use manual correction or adjust confidence if needed. Test overlay
visibility and slide navigation in PowerPoint's full-screen slideshow on the
presentation display. For remote presentations, share that entire display.
Turbo/GPU and Small/CPU are available but were not benchmarked in this check.
