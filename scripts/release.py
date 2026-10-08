"""Validate a version tag and package the complete Windows application folder."""

from __future__ import annotations

import argparse
import ast
import hashlib
import re
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate_version(tag: str, root: Path = ROOT) -> str:
    if not re.fullmatch(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", tag):
        raise ValueError("Release tags must use vMAJOR.MINOR.PATCH, for example v0.1.0")
    version = tag[1:]
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
    if version != project["project"]["version"] or version != runtime_version:
        raise ValueError(
            f"Tag {tag} must match the versions in pyproject.toml and src/vpn_counter/__init__.py"
        )
    return version


def package_release(tag: str, output: Path, root: Path = ROOT) -> Path:
    version = validate_version(tag, root)
    distribution = root / "dist/VPNCounter"
    if not (distribution / "VPNCounter.exe").is_file():
        raise FileNotFoundError("Build dist/VPNCounter/VPNCounter.exe before packaging a release")
    output.mkdir(parents=True, exist_ok=True)
    archive_path = output / f"VPNCounter-{tag}-windows-x64.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(distribution.rglob("*")):
            if path.is_file():
                archive.write(path, Path("VPNCounter") / path.relative_to(distribution))
        archive.write(root / "docs/windows-release.md", "VPNCounter/README.md")
        archive.writestr("VPNCounter/VERSION.txt", version + "\n")
    if archive_path.stat().st_size >= 2 * 1024**3:
        raise ValueError("The archive exceeds GitHub's 2 GiB per-asset limit")
    with archive_path.open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    (output / "SHA256SUMS.txt").write_text(f"{checksum}  {archive_path.name}\n", encoding="utf-8")
    return archive_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/releases")
    arguments = parser.parse_args()
    try:
        version = validate_version(arguments.tag)
        if arguments.verify_only:
            print(f"Verified release version {version}")
        else:
            print(package_release(arguments.tag, arguments.output))
        return 0
    except (ValueError, FileNotFoundError) as error:
        parser.exit(1, f"Release packaging failed: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
