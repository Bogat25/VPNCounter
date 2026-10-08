import hashlib
import importlib.util
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


def test_release_preserves_executable_gpu_files_and_checksum(release_root):
    distribution = release_root / "dist/VPNCounter"
    gpu = distribution / "_internal/nvidia/cudnn/bin"
    gpu.mkdir(parents=True)
    (distribution / "VPNCounter.exe").write_bytes(b"executable fixture")
    (gpu / "cudnn64_9.dll").write_bytes(b"GPU runtime fixture")
    output = release_root / "artifacts/releases"
    archive = release.package_release("v0.1.0", output, release_root)
    with zipfile.ZipFile(archive) as contents:
        assert contents.read("VPNCounter/VPNCounter.exe") == b"executable fixture"
        assert (
            contents.read("VPNCounter/_internal/nvidia/cudnn/bin/cudnn64_9.dll")
            == b"GPU runtime fixture"
        )
        assert contents.read("VPNCounter/VERSION.txt") == b"0.1.0\n"
        assert "Double-click" in contents.read("VPNCounter/README.md").decode()
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert (output / "SHA256SUMS.txt").read_text() == f"{checksum}  {archive.name}\n"
