# VPN Counter for Windows

Choose one Windows download:

- Standalone `.exe`: download and double-click it. No companion folder is needed.
- Folder `.zip`: extract the entire ZIP, open VPNCounter, and double-click
  VPNCounter.exe. Keep the _internal folder next to it. This version starts faster.

Both include Python and GPU runtime libraries. The standalone EXE extracts its
libraries into Windows temporary storage on each launch and removes them on
normal exit. Allow extra startup time and about 3 GB of temporary disk space.

Choose a microphone and your presentation display, then click Start listening.
The default model is Whisper large-v3 on an NVIDIA GPU. The first session
downloads the model and shows its percentage, then loads and warms up recognition.
Subsequent sessions work offline. An NVIDIA driver is
required for GPU recognition. Select Small and CPU for the CPU alternative.

The V icon appears in the Windows tray beside the clock, possibly under the
hidden-icons arrow. Click it to open the control panel. Right-click it for
listening controls, overlay visibility, and Exit VPN Counter. Closing the
control panel keeps the application and counter running in the tray.

Under Presentation overlay, choose a display and use Position to select Top
left, Top right, Bottom left, or Bottom right. Custom (drag) unlocks the counter
so you can move it manually. Lock it again before presenting so clicks pass
through to PowerPoint.

Ctrl+Alt+P starts, pauses, or resumes listening. Ctrl+Alt+Up adds one count,
Ctrl+Alt+Down subtracts one, Ctrl+Alt+R resets, and Ctrl+Alt+O toggles the overlay.

Models and settings are stored in %LOCALAPPDATA%\VPNCounter. Audio stays in
memory and is not uploaded or saved.

This is a portable app. It does not add an Installed apps entry, an installer,
or automatic startup. Click Storage & cleanup in the Recognition panel to open
the data folder or clean up before removing the app. Remove downloaded models
is selected by default; Also remove settings and saved counter is optional.
Clean up and exit waits for recognition to stop, removes the selected data, and
exits. When both options are selected, the empty data folder is also removed.
Removed models download again on the next listening session. Normal exits and
updates preserve the model cache. After cleanup exits, delete the portable
EXE or VPNCounter folder to remove the app. Deleting either alone does not remove
the data in LocalAppData.

Rehearse with the actual microphone and
PowerPoint slideshow before presenting. Share the whole presentation display
for remote presentations so the overlay is included.
