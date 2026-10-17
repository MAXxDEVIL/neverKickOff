# neverKickOff installer for Windows.
#
#   irm https://raw.githubusercontent.com/MAXxDEVIL/neverKickOff/main/install.ps1 | iex
#
# Installs to %LOCALAPPDATA%\neverKickOff and adds a `neverkickoff` command to
# your user PATH. Runs as a string, so PowerShell's execution policy never blocks
# it. Works on Windows PowerShell 5.1 as well as PowerShell 7.
$ErrorActionPreference = 'Stop'

# Windows PowerShell 5.1 on older .NET defaults to TLS 1.0, which GitHub refuses.
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
} catch { }

$repo = 'https://github.com/MAXxDEVIL/neverKickOff'
$dir  = Join-Path $env:LOCALAPPDATA 'neverKickOff'
$binDir = Join-Path $env:LOCALAPPDATA 'Programs\neverKickOff'
$cmd  = Join-Path $binDir 'neverkickoff.cmd'
$venv = Join-Path $dir '.venv'
$venvPy = Join-Path $venv 'Scripts\python.exe'

$zip = Join-Path ([System.IO.Path]::GetTempPath()) 'neverKickOff.zip'
$tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("nko-" + [System.Guid]::NewGuid().ToString('N'))

try {
    # --- 1. a usable python ------------------------------------------------
    $py = $null
    foreach ($name in @('py.exe', 'python.exe')) {
        $found = Get-Command $name -ErrorAction SilentlyContinue
        if ($found) { $py = $found.Source; break }
    }
    if (-not $py) {
        throw "Python 3.8+ not found. Install it from https://www.python.org/downloads/ and tick 'Add python.exe to PATH', then re-run."
    }
    # py.exe can be pointed at Python 2 via PY_PYTHON, so ask it for 3 explicitly.
    $py3 = @()
    if ($py -like '*\py.exe') { $py3 = @('-3') }
    & $py @py3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"
    if ($LASTEXITCODE -ne 0) { throw "Python 3.8 or newer is required." }
    Write-Host "python   : $py"
    if ($py -like '*\WindowsApps\*') {
        Write-Host "  warning: that is the Microsoft Store alias. If it opens the Store" -ForegroundColor Yellow
        Write-Host "           instead of running, install Python from python.org." -ForegroundColor Yellow
    }

    # --- 2. download the source -------------------------------------------
    Write-Host "download : $repo"
    try {
        (New-Object System.Net.WebClient).DownloadFile("$repo/archive/refs/heads/main.zip", $zip)
    } catch {
        throw "download failed: $($_.Exception.Message)"
    }
    Expand-Archive -Path $zip -DestinationPath $tmp -Force

    $src = Join-Path $tmp 'neverKickOff-main'
    if (-not (Test-Path (Join-Path $src 'gui.py'))) { throw "unexpected archive layout (no gui.py)." }

    # Copying over an existing install leaves .venv alone, so re-running upgrades.
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    Get-ChildItem -Path $src -Force | Copy-Item -Destination $dir -Recurse -Force

    # --- 3. virtualenv + dependencies -------------------------------------
    if (-not (Test-Path $venvPy)) {
        Write-Host "venv     : creating"
        & $py @py3 -m venv $venv
        if ($LASTEXITCODE -ne 0) {
            Remove-Item -Recurse -Force $venv -ErrorAction SilentlyContinue
            throw "could not create a virtualenv at $venv"
        }
    }

    Write-Host "deps     : installing"
    & $venvPy -m pip install --disable-pip-version-check `
        -r "$dir\requirements.txt" -r "$dir\requirements-tray.txt"
    if ($LASTEXITCODE -ne 0) { throw "pip install failed." }

    # --- 4. launcher ------------------------------------------------------
    New-Item -ItemType Directory -Force -Path $binDir | Out-Null
    $cmdText = @"
@echo off
"$venvPy" "$dir\gui.py" %*
"@
    Set-Content -Path $cmd -Value $cmdText -Encoding ASCII

    # --- 5. put the launcher on the user PATH -----------------------------
    # Read the registry value unexpanded: GetEnvironmentVariable('Path','User')
    # expands %VARS% and would write the expansion back, bloating your PATH.
    $pathAdded = $false
    try {
        $key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Environment', $true)
        if ($key) {
            $raw = $key.GetValue('Path', '', [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
            if ($null -eq $raw) { $raw = '' }
            if (-not (($raw -split ';') -contains $binDir)) {
                if ($raw -eq '') { $joined = $binDir } else { $joined = $raw.TrimEnd(';') + ';' + $binDir }
                $key.SetValue('Path', $joined, [Microsoft.Win32.RegistryValueKind]::ExpandString)
                $pathAdded = $true
            }
            $key.Close()
        }
    } catch {
        Write-Host "  warning: could not update your PATH automatically." -ForegroundColor Yellow
        Write-Host "           Add $binDir to it by hand." -ForegroundColor Yellow
    }

    # --- 6. what is still missing -----------------------------------------
    $tkOk = $true
    try {
        & $venvPy -c "import tkinter" 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { $tkOk = $false }
    } catch { $tkOk = $false }

    # --- 7. report --------------------------------------------------------
    Write-Host ""
    Write-Host "neverKickOff installed."
    Write-Host "  source : $dir"
    Write-Host "  run    : neverkickoff          (in a NEW terminal)"
    Write-Host "  or     : $venvPy $dir\gui.py"
    Write-Host "  verify : $venvPy $dir\test_engine.py"
    if ($pathAdded) {
        Write-Host ""
        Write-Host "Added $binDir to your PATH - open a new terminal for it to apply."
    }
    if (-not $tkOk) {
        Write-Host ""
        Write-Host "tkinter is missing, so the GUI cannot start." -ForegroundColor Yellow
        Write-Host "Reinstall Python from python.org with the 'tcl/tk and IDLE' option," -ForegroundColor Yellow
        Write-Host "or run the CLI instead: $venvPy $dir\main.py" -ForegroundColor Yellow
    }
} finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
    Remove-Item -Force $zip -ErrorAction SilentlyContinue
}
