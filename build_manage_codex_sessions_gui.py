from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
ENTRY_SCRIPT = REPO_ROOT / "manage_codex_sessions_gui.py"
BUILD_REQUIREMENTS = REPO_ROOT / "requirements-build.txt"
APP_NAME = "manage_codex_sessions_gui"
ICON_PATH = REPO_ROOT / "assets" / "manage_codex_sessions.ico"
HIDDEN_IMPORTS = [
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
]
EXCLUDED_MODULES = [
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
]


def run_command(command: list[str]) -> None:
    print("+", shlex.join(command))
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def install_build_dependencies(python_executable: str) -> None:
    run_command([python_executable, "-m", "pip", "install", "--upgrade", "pip"])
    run_command([
        python_executable,
        "-m",
        "pip",
        "install",
        "-r",
        str(BUILD_REQUIREMENTS),
    ])


def build_pyinstaller_command(one_dir: bool, python_executable: str, extra_args: list[str]) -> list[str]:
    command = [
        python_executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        APP_NAME,
    ]

    command.append("--onedir" if one_dir else "--onefile")

    if ICON_PATH.exists():
        add_data_separator = ";" if sys.platform.startswith("win") else ":"
        command.extend(["--icon", str(ICON_PATH)])
        command.extend(["--add-data", f"{ICON_PATH}{add_data_separator}assets"])

    for module_name in HIDDEN_IMPORTS:
        command.extend(["--hidden-import", module_name])

    for module_name in EXCLUDED_MODULES:
        command.extend(["--exclude-module", module_name])

    command.extend(extra_args)
    command.append(str(ENTRY_SCRIPT))
    return command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the Qt GUI executable for the current platform with PyInstaller."
    )
    parser.add_argument(
        "--onedir",
        action="store_true",
        help="Build a directory bundle instead of a single-file executable.",
    )
    parser.add_argument(
        "--skip-dependency-install",
        action="store_true",
        help="Skip installing/upgrading packages from requirements-build.txt.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python interpreter used to install build dependencies and run PyInstaller. Defaults to the current interpreter.",
    )
    parser.add_argument(
        "pyinstaller_args",
        nargs=argparse.REMAINDER,
        help="Extra arguments passed through to PyInstaller. Prefix with '--' to separate them from this script's options.",
    )
    return parser


def normalize_pyinstaller_args(extra_args: list[str]) -> list[str]:
    if extra_args and extra_args[0] == "--":
        return extra_args[1:]
    return extra_args


def main() -> int:
    parser = build_parser()
    arguments = parser.parse_args()
    extra_args = normalize_pyinstaller_args(arguments.pyinstaller_args)

    if not arguments.skip_dependency_install:
        install_build_dependencies(arguments.python)

    run_command(build_pyinstaller_command(arguments.onedir, arguments.python, extra_args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
