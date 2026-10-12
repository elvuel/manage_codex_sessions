param(
    [switch]$OneDir,
    [switch]$SkipDependencyInstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = $PSScriptRoot
Set-Location $repoRoot

$arguments = @('build_manage_codex_sessions_gui.py')

if ($OneDir) {
    $arguments += '--onedir'
}

if ($SkipDependencyInstall) {
    $arguments += '--skip-dependency-install'
}

python @arguments
