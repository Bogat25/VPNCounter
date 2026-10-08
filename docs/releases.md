# Tag-based Windows releases

`.github/workflows/release.yml` runs when a version tag such as `v0.1.0` is
published to GitHub. Normal branch commits do not publish a release. The tagged
commit must contain the workflow. This uses GitHub's
[tag push trigger](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#push).

## Prepare a version

1. Set the same version in `pyproject.toml` and
   `src/vpn_counter/__init__.py`, for example `0.1.0`.
2. Run `uv lock`, check the app, and commit the version locally on `main`.
3. Tag that commit, for example `git tag -a v0.1.0 -m "VPN Counter v0.1.0"`.
4. Publish the committed source and that tag to GitHub using your Git client
   when you want the release to run. Creating a local tag alone does not run it.

Only stable `vMAJOR.MINOR.PATCH` tags are accepted. Invalid tags or a mismatch
with either source version fail before the application build. Keep the version
in `uv.lock` current after changing `pyproject.toml`.

## What the workflow does

The Windows x64 release job installs Python 3.12.10, uv 0.11.17, and the exact
dependencies from `uv.lock`, including GPU and build extras. It runs lint,
formatting checks, and tests, builds the PyInstaller folder, and exercises the
frozen UI and speech imports without opening a microphone or loading a model.
The hosted runner does not need an NVIDIA GPU. Actual CUDA inference remains
covered by a separate check on the presentation computer.

`scripts/release.py` creates these files:

- `VPNCounter-v0.1.0-windows-x64.zip`, with the full application folder, GPU
  runtime libraries, Windows launch instructions, and `VERSION.txt`.
- `SHA256SUMS.txt`, with the archive's SHA-256 checksum.

The archive must remain below GitHub's
[2 GiB limit per release asset](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases#storage-and-bandwidth-quotas).
Speech models are downloaded at first use and are not part of the ZIP.

The final step verifies the checksum, then uses
[`gh release create`](https://cli.github.com/manual/gh_release_create) to publish
release notes and attach both files to the existing tag. The ZIP is uploaded
directly from the build runner without an intermediate Actions artifact copy.
The release job receives `contents: write`, uses GitHub's built-in token only
in the publication step, and does not persist checkout credentials. No personal
access token or additional secret is needed. Action versions are pinned to their
public commit IDs.

An existing release is not overwritten: attempting to publish the same release
again fails. Use a new version tag for a new release.

## Check the same build locally

```powershell
.\scripts\build.ps1
$appProcess = Start-Process -FilePath '.\dist\VPNCounter\VPNCounter.exe' -ArgumentList @('--smoke-test', 'artifacts/packaged-smoke.json') -PassThru -WindowStyle Hidden
$appProcess.WaitForExit()
.venv\Scripts\python.exe scripts/release.py --tag v0.1.0
```

The ZIP and checksum are saved under `artifacts/releases/`. The smoke report is
local and sets `ok` to `true` on success. These commands build local files; they
do not create tags, contact the GitHub release API, or publish anything.
