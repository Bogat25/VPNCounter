# Tag-based Windows releases

`.github/workflows/release.yml` runs when a version tag such as `v0.1.4` is
published to GitHub. Normal branch commits do not publish a release. The tagged
commit must contain the workflow. This uses GitHub's
[tag push trigger](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#push).

## Prepare a version

1. Check the app and commit the source locally on `main`.
2. Tag that commit with the version to release, for example
   `git tag -a v0.1.4 -m "VPN Counter v0.1.4"`.
3. Publish the committed source and that tag to GitHub using your Git client
   when you want the release to run. Creating a local tag alone does not run it.

Only stable `vMAJOR.MINOR.PATCH` tags are accepted. The tag determines the built
app's version. Before installing dependencies, the workflow runs
`scripts/release.py --tag <tag> --prepare` to apply that version to
`pyproject.toml`, `src/vpn_counter/__init__.py`, and the app entry in `uv.lock`.
Other dependency versions and hashes remain unchanged. These edits are local
to the build checkout; the workflow does not commit them back to the repository.
Manual version edits are not required for each new tag. The normal development
checkout retains its recorded version until explicitly prepared for a release.

A failed tag created before this workflow change still points to the old
workflow. Pushing a branch update and rerunning that old job will not use the
fix. Publish a new version tag on the fixed commit, or recreate the failed tag
there using your Git client. Keep successfully released tags unchanged.

## What the workflow does

The Windows x64 release job installs Python 3.12.10, uv 0.11.17, and the exact
dependencies from `uv.lock`, including GPU and build extras. It runs lint,
formatting checks, and tests, then builds both the PyInstaller folder and a
standalone EXE from the same analyzed dependencies. It exercises both frozen
UIs and speech imports without opening a microphone or loading a model.
Each smoke report must show the exact version from the release tag. The check
allows up to three minutes per launch for the standalone EXE's extraction.
The hosted runner does not need an NVIDIA GPU. Actual CUDA inference remains
covered by a separate check on the presentation computer.

`scripts/release.py` creates these files:

- `VPNCounter-v0.1.4-windows-x64.exe`, a standalone portable app containing its
  Python, Qt, audio, and GPU dependencies. Download and run this file directly.
- `VPNCounter-v0.1.4-windows-x64.zip`, with the full application folder, GPU
  runtime libraries, Windows launch instructions, and `VERSION.txt`.
- `SHA256SUMS.txt`, with SHA-256 checksums for both downloads.

Each download must remain below GitHub's
[2 GiB limit per release asset](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases#storage-and-bandwidth-quotas).
Speech models download at first use and are not part of either download. Both
formats use the same models and settings in `%LOCALAPPDATA%\VPNCounter`.
The standalone EXE extracts its libraries into temporary storage on each launch,
then removes them on normal exit. The folder version starts faster.

The final step runs `scripts/release.py --verify-assets` to verify both hashes
and asset sizes, then uses
[`gh release create`](https://cli.github.com/manual/gh_release_create) to publish
release notes and attach all three files to the existing tag. The notes begin
with the download instructions in [release-notes.md](release-notes.md), followed
by GitHub's generated changelog. Both app downloads are uploaded
directly from the build runner without an intermediate Actions artifact copy.
The release job receives `contents: write`, uses GitHub's built-in token only
in the publication step, and does not persist checkout credentials. No personal
access token or additional secret is needed. Action versions are pinned to their
public commit IDs.

An existing release is not overwritten: attempting to publish the same release
again fails. Use a new version tag for a new release.

## Check the same build locally

```powershell
.venv\Scripts\python.exe scripts/release.py --tag v0.1.4 --prepare
.\scripts\build.ps1
$checks = @{
  '.\dist\VPNCounter\VPNCounter.exe' = 'artifacts/folder-smoke.json'
  '.\dist\VPNCounter-portable.exe' = 'artifacts/portable-smoke.json'
}
foreach ($check in $checks.GetEnumerator()) {
  $appProcess = Start-Process -FilePath $check.Key -ArgumentList @('--smoke-test', $check.Value) -PassThru -WindowStyle Hidden
  if (-not $appProcess.WaitForExit(180000)) { throw 'Smoke check timed out.' }
  if ($appProcess.ExitCode -ne 0) { throw 'Smoke check failed.' }
}
.venv\Scripts\python.exe scripts/release.py --tag v0.1.4
.venv\Scripts\python.exe scripts/release.py --tag v0.1.4 --verify-assets
```

The EXE, ZIP, and checksum are saved under `artifacts/releases/`. Each smoke
report is local and sets `ok` to `true` on success. These commands build local files; they
do not create tags, contact the GitHub release API, or publish anything.
The preparation command changes the three local app version entries. Packaging
still checks that they all match the requested tag, so prepare before building.
Exit any running packaged copy before rebuilding;
`build.ps1` checks this before replacing files. For a PyInstaller build in another
location, pass `--distribution <path-to-VPNCounter-folder>` to `release.py`.
It looks for `VPNCounter-portable.exe` beside that folder. Override this with
`--portable-executable <path-to-standalone-exe>` when necessary.

The existing v0.1.3 release contains the folder ZIP. Publish a new tag on the
commit that adds the standalone build, such as v0.1.4, to get both formats.
Rerunning the old tag continues to use its old workflow.
