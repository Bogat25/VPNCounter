# VPN Counter for Windows

Extract the entire ZIP, open the VPNCounter folder, and double-click
VPNCounter.exe. Keep the _internal folder next to the executable.
Python does not need to be installed separately.

Choose a microphone and your presentation display, then click Start listening.
The default model is Whisper large-v3 on an NVIDIA GPU. The first session
downloads the model; subsequent sessions work offline. An NVIDIA driver is
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
memory and is not uploaded or saved. Rehearse with the actual microphone and
PowerPoint slideshow before presenting. Share the whole presentation display
for remote presentations so the overlay is included.
