"""Prepare a tagged build, validate its version, and package the Windows app."""

from __future__ import annotations

import argparse
import ast
import hashlib
import re
import shutil
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_ASSET_SIZE = 2 * 1024**3


def version_from_tag(tag: str) -> str:
    if not re.fullmatch(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", tag):
        raise ValueError("Release tags must use vMAJOR.MINOR.PATCH, for example v0.1.0")
    return tag[1:]


def validate_version(tag: str, root: Path = ROOT) -> str:
    version = version_from_tag(tag)
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    module = ast.parse((root / "src/vpn_counter/__init__.py").read_text(encoding="utf-8"))
    runtime_version = next(
        (
            ast.literal_eval(node.value)
            for node in module.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "__version__"
                for target in node.targets
            )
        ),
        None,
    )
    lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    locked_versions = [
        package.get("version")
        for package in lock.get("package", [])
        if package.get("name") == "vpn-counter" and package.get("source") == {"editable": "."}
    ]
    if (
        version != project["project"]["version"]
        or version != runtime_version
        or locked_versions != [version]
    ):
        raise ValueError(
            f"Tag {tag} must match pyproject.toml, src/vpn_counter/__init__.py, and uv.lock. "
            "Run this script with --prepare before building the executable."
        )
    return version


def _stamp_assignment(text: str, key: str, version: str) -> str:
    pattern = (
        rf"(?m)^({re.escape(key)}[ \t]*=[ \t]*)"
        r"(?:\"[^\"\r\n]*\"|'[^'\r\n]*')([ \t]*(?:#[^\r\n]*)?)$"
    )
    result, count = re.subn(pattern, lambda match: f'{match[1]}"{version}"{match[2]}', text)
    if count != 1:
        raise ValueError(f"Expected exactly one {key} assignment in the version section")
    return result


def _stamp_table(text: str, header: str, version: str, *, package: bool = False) -> str:
    # Keep dependency pins, hashes, comments, and unrelated version fields intact.
    tomllib.loads(text)
    blocks = re.split(r"(?m)(?=^\[)", text)
    count = 0
    for index, block in enumerate(blocks):
        if block.partition("\n")[0].split("#", 1)[0].strip() != header:
            continue
        if package:
            entry = tomllib.loads(block)["package"][0]
            if entry.get("name") != "vpn-counter" or entry.get("source") != {"editable": "."}:
                continue
        blocks[index] = _stamp_assignment(block, "version", version)
        count += 1
    if count != 1:
        raise ValueError(f"Expected exactly one app version section {header}")
    return "".join(blocks)


def prepare_version(tag: str, root: Path = ROOT) -> str:
    """Apply a tag's version to this checkout without changing dependency pins."""
    version = version_from_tag(tag)
    project = root / "pyproject.toml"
    source = root / "src/vpn_counter/__init__.py"
    lock = root / "uv.lock"
    source_text = source.read_text(encoding="utf-8")
    ast.parse(source_text)
    # Compute and validate every replacement before writing any files.
    updates = {
        project: _stamp_table(project.read_text(encoding="utf-8"), "[project]", version),
        source: _stamp_assignment(source_text, "__version__", version),
        lock: _stamp_table(lock.read_text(encoding="utf-8"), "[[package]]", version, package=True),
    }
    for path, contents in updates.items():
        path.write_text(contents, encoding="utf-8", newline="\n")
    return validate_version(tag, root)


def release_assets(tag: str, output: Path) -> tuple[Path, Path]:
    version_from_tag(tag)
    name = f"VPNCounter-{tag}-windows-x64"
    return output / f"{name}.zip", output / f"{name}.exe"


def checksums(assets: tuple[Path, Path]) -> str:
    lines = []
    for asset in assets:
        with asset.open("rb") as stream:
            checksum = hashlib.file_digest(stream, "sha256").hexdigest()
        lines.append(f"{checksum}  {asset.name}\n")
    return "".join(lines)


def verify_release(tag: str, output: Path, root: Path = ROOT) -> tuple[Path, Path]:
    validate_version(tag, root)
    assets = release_assets(tag, output)
    for asset in assets:
        if not asset.is_file():
            raise FileNotFoundError(f"Missing release asset: {asset.name}")
        if asset.stat().st_size >= MAX_ASSET_SIZE:
            raise ValueError(f"{asset.name} exceeds GitHub's 2 GiB per-asset limit")
    if (output / "SHA256SUMS.txt").read_text(encoding="utf-8") != checksums(assets):
        raise ValueError("Release asset checksums do not match SHA256SUMS.txt")
    return assets


def package_release(
    tag: str,
    output: Path,
    root: Path = ROOT,
    *,
    distribution: Path | None = None,
    portable_executable: Path | None = None,
) -> Path:
    version = validate_version(tag, root)
    distribution = distribution or root / "dist/VPNCounter"
    portable_executable = portable_executable or distribution.parent / "VPNCounter-portable.exe"
    if not (distribution / "VPNCounter.exe").is_file():
        raise FileNotFoundError(
            f"Build {distribution / 'VPNCounter.exe'} before packaging a release"
        )
    if not portable_executable.is_file():
        raise FileNotFoundError(f"Build {portable_executable} before packaging a release")
    if portable_executable.stat().st_size >= MAX_ASSET_SIZE:
        raise ValueError("The portable executable exceeds GitHub's 2 GiB per-asset limit")
    output.mkdir(parents=True, exist_ok=True)
    assets = release_assets(tag, output)
    archive_path, executable_path = assets
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(distribution.rglob("*")):
            if path.is_file():
                archive.write(path, Path("VPNCounter") / path.relative_to(distribution))
        archive.write(root / "docs/windows-release.md", "VPNCounter/README.md")
        archive.writestr("VPNCounter/VERSION.txt", version + "\n")
    if archive_path.stat().st_size >= MAX_ASSET_SIZE:
        raise ValueError("The archive exceeds GitHub's 2 GiB per-asset limit")
    shutil.copyfile(portable_executable, executable_path)
    (output / "SHA256SUMS.txt").write_text(checksums(assets), encoding="utf-8")
    return archive_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verify-only", action="store_true")
    mode.add_argument("--verify-assets", action="store_true", help="Verify both release downloads")
    mode.add_argument(
        "--prepare", action="store_true", help="Apply the tag version before building"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/releases")
    parser.add_argument(
        "--distribution", type=Path, help="Use an application folder from a custom build"
    )
    parser.add_argument(
        "--portable-executable", type=Path, help="Use a standalone EXE from a custom build"
    )
    arguments = parser.parse_args()
    try:
        if arguments.prepare:
            print(f"Prepared release version {prepare_version(arguments.tag)}")
            return 0
        version = validate_version(arguments.tag)
        if arguments.verify_only:
            print(f"Verified release version {version}")
        elif arguments.verify_assets:
            verify_release(arguments.tag, arguments.output)
            print("Verified Windows ZIP and portable EXE checksums")
        else:
            package_release(
                arguments.tag,
                arguments.output,
                distribution=arguments.distribution,
                portable_executable=arguments.portable_executable,
            )
            for asset in release_assets(arguments.tag, arguments.output):
                print(asset)
            print(arguments.output / "SHA256SUMS.txt")
        return 0
    except (ValueError, OSError) as error:
        parser.exit(1, f"Release packaging failed: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
