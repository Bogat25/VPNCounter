Choose either Windows download:

- **`.exe`**: standalone portable app. Download and run it directly.
- **`.zip`**: folder version. Extract everything and run `VPNCounter.exe` inside;
  keep its `_internal` folder alongside it. This version starts faster.

Both include the app and GPU libraries. Python and installation are not required.
The standalone EXE unpacks libraries into Windows temporary storage at launch
and removes them on normal exit, so allow extra startup time and disk space.
Speech models download on first use to `%LOCALAPPDATA%\VPNCounter`; later
sessions work offline. Use **Storage & cleanup** before removing the app if you
also want to delete its downloaded models and settings.

Model, CPU/GPU, and microphone settings remain editable during a session without
cleanup. Active listening restarts with the latest choices after the current
operation finishes; changes while paused wait for Start listening.

To update, exit the running copy through **Exit VPN Counter** in the V tray menu,
then open the new EXE. Closing the panel leaves the previous copy running.
Your settings, count, and downloaded models are kept when switching app versions.

The **Source code** downloads are for development; choose a Windows asset to use
the app.
