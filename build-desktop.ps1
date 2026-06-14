#!/usr/bin/env pwsh
# Build the HEA-Bench desktop app and drop the installers at the repo root.
#
# The desktop app is an offline Tauri wrapper of the single web page
# (web/index.html). Tauri writes the installers deep under
# src-tauri/target/release/bundle/; this wrapper builds and then copies
# them to the repository root as HEA-Bench-Setup-x64.exe (NSIS) and
# HEA-Bench-x64.msi (MSI) -- the same stable names used for the GitHub
# release assets. Those root copies are gitignored.
#
# Usage:  ./build-desktop.ps1     (run from anywhere; it cd's to its own dir)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Make cargo / tauri-cli / node visible regardless of how the shell launched.
$env:PATH = [Environment]::GetEnvironmentVariable('PATH','Machine') + ';' +
            [Environment]::GetEnvironmentVariable('PATH','User') + ';' +
            "$env:USERPROFILE\.cargo\bin;C:\Program Files\nodejs;$env:APPDATA\npm"

if (-not (Get-Command cargo-tauri -ErrorAction SilentlyContinue)) {
    Write-Host "Installing the Tauri CLI (one time)..."
    cargo install tauri-cli --version "^2.0" --locked
}

Write-Host "Building the desktop app (offline wrapper of web/index.html)..."
cargo tauri build

$bundle = "src-tauri/target/release/bundle"
$exe = (Get-ChildItem "$bundle/nsis/*-setup.exe")[0]
$msi = (Get-ChildItem "$bundle/msi/*.msi")[0]
Copy-Item $exe.FullName "HEA-Bench-Setup-x64.exe" -Force
Copy-Item $msi.FullName "HEA-Bench-x64.msi" -Force

Write-Host ""
Write-Host "Done. Installers written to the repo root:"
Get-Item "HEA-Bench-Setup-x64.exe", "HEA-Bench-x64.msi" |
    ForEach-Object { "  {0}  ({1:N1} MB)" -f $_.Name, ($_.Length / 1MB) }
