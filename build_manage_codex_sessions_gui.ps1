param(
    [switch]$OneDir,
    [switch]$SkipDependencyInstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = $PSScriptRoot
Set-Location $repoRoot

if (-not $SkipDependencyInstall) {
    python -m pip install --upgrade pip
    python -m pip install pyinstaller PySide6
}

$arguments = @(
    '-m',
    'PyInstaller',
    '--noconfirm',
    '--clean',
    '--windowed',
    '--name',
    'manage_codex_sessions_gui',
    '--hidden-import',
    'PySide6',
    '--hidden-import',
    'PySide6.QtCore',
    '--hidden-import',
    'PySide6.QtGui',
    '--hidden-import',
    'PySide6.QtWidgets',
    '--exclude-module',
    'PySide6.QtWebEngineCore',
    '--exclude-module',
    'PySide6.QtWebEngineWidgets',
    '--exclude-module',
    'PySide6.QtWebEngineQuick',
    'manage_codex_sessions_gui.py'
)

if ($OneDir) {
    $arguments = @('-m', 'PyInstaller', '--onedir') + $arguments[2..($arguments.Length - 1)]
} else {
    $arguments = @('-m', 'PyInstaller', '--onefile') + $arguments[2..($arguments.Length - 1)]
}

python @arguments
