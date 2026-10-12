from __future__ import annotations

import argparse
import hashlib
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
DIST_DIR = REPO_ROOT / "dist"
APP_NAME = "manage_codex_sessions_gui"


def normalize_runner_os(value: str) -> str:
    normalized = value.strip().lower()
    mapping = {
        "windows": "windows",
        "linux": "linux",
        "macos": "macos",
        "mac": "macos",
        "darwin": "macos",
    }
    return mapping.get(normalized, normalized)


def normalize_runner_arch(value: str) -> str:
    normalized = value.strip().lower()
    mapping = {
        "x64": "x86_64",
        "amd64": "x86_64",
        "x86_64": "x86_64",
        "arm64": "arm64",
        "aarch64": "arm64",
        "x86": "x86",
    }
    return mapping.get(normalized, normalized)


def slugify_tag(tag: str) -> str:
    slug = tag.strip().replace("/", "-").replace("\\", "-")
    return slug or "untagged"


def resolve_source_path(runner_os: str) -> Path:
    if runner_os == "windows":
        source = DIST_DIR / f"{APP_NAME}.exe"
        if source.exists():
            return source
    elif runner_os == "macos":
        app_bundle = DIST_DIR / f"{APP_NAME}.app"
        if app_bundle.exists():
            return app_bundle
    source = DIST_DIR / APP_NAME
    if source.exists():
        return source
    raise FileNotFoundError(f"No release artifact found in {DIST_DIR} for platform {runner_os!r}.")


def stage_source(source: Path, root: Path) -> Path:
    destination = root / source.name
    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)
    return destination


def write_zip(archive_path: Path, staged_path: Path, temp_root: Path) -> None:
    with zipfile.ZipFile(archive_path, mode="w", compression=zipfile.ZIP_DEFLATED) as handle:
        if staged_path.is_dir():
            for path in sorted(staged_path.rglob("*")):
                if path.is_file():
                    handle.write(path, arcname=path.relative_to(temp_root))
        else:
            handle.write(staged_path, arcname=staged_path.relative_to(temp_root))


def write_tar_gz(archive_path: Path, staged_path: Path) -> None:
    with tarfile.open(archive_path, mode="w:gz") as handle:
        handle.add(staged_path, arcname=staged_path.name)


def write_sha256_file(archive_path: Path) -> Path:
    digest = hashlib.sha256()
    with archive_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    checksum_path = archive_path.with_name(f"{archive_path.name}.sha256")
    checksum_path.write_text(f"{digest.hexdigest()}  {archive_path.name}\n", encoding="utf-8")
    return checksum_path


def build_archive_name(tag: str, runner_os: str, runner_arch: str, source: Path) -> str:
    tag_slug = slugify_tag(tag)
    platform_slug = f"{runner_os}-{runner_arch}"
    suffix = ".zip" if runner_os == "windows" else ".tar.gz"
    source_slug = source.stem if source.suffix else source.name
    return f"{source_slug}-{tag_slug}-{platform_slug}{suffix}"


def package_release_asset(tag: str, runner_os: str, runner_arch: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    normalized_os = normalize_runner_os(runner_os)
    normalized_arch = normalize_runner_arch(runner_arch)
    source = resolve_source_path(normalized_os)
    archive_path = output_dir / build_archive_name(tag, normalized_os, normalized_arch, source)

    with tempfile.TemporaryDirectory(prefix="release-asset-", dir=output_dir) as temp_dir:
        temp_root = Path(temp_dir)
        staged_path = stage_source(source, temp_root)
        if normalized_os == "windows":
            write_zip(archive_path, staged_path, temp_root)
        else:
            write_tar_gz(archive_path, staged_path)

    write_sha256_file(archive_path)

    return archive_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Package a built GUI artifact into a GitHub release asset.")
    parser.add_argument("--tag", required=True, help="Git tag to embed in the release asset name.")
    parser.add_argument("--runner-os", required=True, help="Runner operating system, for example Windows, Linux, or macOS.")
    parser.add_argument("--runner-arch", required=True, help="Runner architecture, for example X64 or ARM64.")
    parser.add_argument("--output-dir", default="release-artifacts", help="Directory where the packaged asset will be written.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    archive_path = package_release_asset(
        tag=args.tag,
        runner_os=args.runner_os,
        runner_arch=args.runner_arch,
        output_dir=(REPO_ROOT / args.output_dir).resolve(),
    )
    print(archive_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
