import hashlib
import importlib.util
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

import pytest

script_path = Path(__file__).resolve().parents[1] / "scripts/release.py"
spec = importlib.util.spec_from_file_location("release_script", script_path)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


@pytest.fixture
def release_root(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.1.0"\n')
    source = tmp_path / "src/vpn_counter"
    source.mkdir(parents=True)
    (source / "__init__.py").write_text('__version__ = "0.1.0"\n')
    (tmp_path / "uv.lock").write_text(
        'version = 1\n\n[[package]]\nname = "vpn-counter"\nversion = "0.1.0"\n'
        'source = { editable = "." }\n\n'
        '[[package]]\nname = "other-package"\nversion = "0.1.0"\n'
        'source = { registry = "https://pypi.org/simple" }\n'
    )
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "windows-release.md").write_text("Double-click VPNCounter.exe.\n")
    return tmp_path


@pytest.mark.parametrize("tag", ["0.1.0", "v0.1", "v01.1.0", "v0.2.0", "v0.1.0;echo bad"])
def test_invalid_or_mismatched_tag_is_rejected(release_root, tag):
    with pytest.raises(ValueError):
        release.validate_version(tag, release_root)


def test_runtime_version_must_match_tag(release_root):
    (release_root / "src/vpn_counter/__init__.py").write_text('__version__ = "0.2.0"\n')
    with pytest.raises(ValueError):
        release.validate_version("v0.1.0", release_root)


def test_lockfile_app_version_must_match_tag(release_root):
    lock = release_root / "uv.lock"
    lock.write_text(lock.read_text().replace('version = "0.1.0"', 'version = "0.0.9"', 1))
    with pytest.raises(ValueError, match="uv.lock"):
        release.validate_version("v0.1.0", release_root)


@pytest.mark.parametrize("tag", ["v0.1.2", "v1.0.0", "v12.34.56"])
def test_new_tag_sets_all_app_versions_without_changing_dependency_pins(release_root, tag):
    lock = release_root / "uv.lock"
    previous = tomllib.loads(lock.read_text())
    assert release.prepare_version(tag, release_root) == tag[1:]
    assert release.validate_version(tag, release_root) == tag[1:]
    updated = tomllib.loads(lock.read_text())
    assert updated["package"][1:] == previous["package"][1:]
    previous["package"][0]["version"] = tag[1:]
    assert updated == previous
    contents = {path: path.read_bytes() for path in release_root.rglob("*") if path.is_file()}
    release.prepare_version(tag, release_root)
    assert contents == {path: path.read_bytes() for path in contents}


@pytest.mark.parametrize("tag", ["0.1.2", "v0.1", "v01.1.2", "v0.1.2-rc1", "v0.١.٢"])
def test_prepare_rejects_invalid_tags_without_changing_files(release_root, tag):
    contents = {path: path.read_bytes() for path in release_root.rglob("*") if path.is_file()}
    with pytest.raises(ValueError):
        release.prepare_version(tag, release_root)
    assert contents == {path: path.read_bytes() for path in contents}


@pytest.mark.parametrize("filename", ["pyproject.toml", "src/vpn_counter/__init__.py", "uv.lock"])
def test_incomplete_version_metadata_cannot_partially_update_checkout(release_root, filename):
    path = release_root / filename
    key = "__version__" if filename.endswith(".py") else "version"
    path.write_text(path.read_text().replace(f'{key} = "0.1.0"', 'other = "0.1.0"'))
    contents = {path: path.read_bytes() for path in release_root.rglob("*") if path.is_file()}
    with pytest.raises(ValueError):
        release.prepare_version("v0.1.2", release_root)
    assert contents == {path: path.read_bytes() for path in contents}


def test_workflow_prepare_command_accepts_next_tag_from_old_source(release_root):
    script = release_root / "scripts/release.py"
    script.parent.mkdir()
    shutil.copyfile(script_path, script)
    for mode in ("--prepare", "--verify-only"):
        result = subprocess.run(
            [sys.executable, str(script), "--tag", "v0.1.2", mode],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
    assert release.validate_version("v0.1.2", release_root) == "0.1.2"


@pytest.mark.parametrize("custom_folder", [False, True])
def test_release_preserves_executable_gpu_files_and_checksum(release_root, custom_folder):
    release.prepare_version("v0.1.2", release_root)
    distribution = release_root / (
        "separate-build/VPNCounter" if custom_folder else "dist/VPNCounter"
    )
    gpu = distribution / "_internal/nvidia/cudnn/bin"
    gpu.mkdir(parents=True)
    (distribution / "VPNCounter.exe").write_bytes(b"executable fixture")
    (gpu / "cudnn64_9.dll").write_bytes(b"GPU runtime fixture")
    output = release_root / "artifacts/releases"
    archive = release.package_release(
        "v0.1.2", output, release_root, distribution=distribution if custom_folder else None
    )
    assert archive.name == "VPNCounter-v0.1.2-windows-x64.zip"
    with zipfile.ZipFile(archive) as contents:
        assert contents.read("VPNCounter/VPNCounter.exe") == b"executable fixture"
        assert (
            contents.read("VPNCounter/_internal/nvidia/cudnn/bin/cudnn64_9.dll")
            == b"GPU runtime fixture"
        )
        assert contents.read("VPNCounter/VERSION.txt") == b"0.1.2\n"
        assert "Double-click" in contents.read("VPNCounter/README.md").decode()
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert (output / "SHA256SUMS.txt").read_text() == f"{checksum}  {archive.name}\n"
