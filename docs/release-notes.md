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

The **Source code** downloads are for development; choose a Windows asset to use
the app.
