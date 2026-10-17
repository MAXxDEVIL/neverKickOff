# neverKickOff compiled-binary installer for Windows.
#
#   irm https://raw.githubusercontent.com/MAXxDEVIL/neverKickOff/main/install-rust.ps1 | iex
#
# Downloads the prebuilt x86-64 binary from the latest GitHub release, checks its
# SHA-256, installs it into %LOCALAPPDATA%\Programs\neverKickOff, and adds that
# folder to your user PATH. Runs as a string, so PowerShell's execution policy
# never blocks it. Works on Windows PowerShell 5.1 as well as PowerShell 7.
#
# Env:
#   NKO_VERSION=v1.0.0     install that release instead of the latest
#   NKO_BASE_URL=<url>     download from somewhere else (used by the tests)
$ErrorActionPreference = 'Stop'

# Windows PowerShell 5.1 on older .NET defaults to TLS 1.0, which GitHub refuses.
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
} catch { }

$repo   = 'MAXxDEVIL/neverKickOff'
$target = 'x86_64-pc-windows-msvc'
$asset  = "neverkickoff-$target.zip"

function Say($msg) { Write-Host $msg }
function Die($msg) { throw "install: $msg" }

# A 32-bit PowerShell on 64-bit Windows reports x86 and hides the real CPU in
# PROCESSOR_ARCHITEW6432, so check both before giving up.
$arch = $env:PROCESSOR_ARCHITECTURE
if ($env:PROCESSOR_ARCHITEW6432) { $arch = $env:PROCESSOR_ARCHITEW6432 }
if ($arch -ne 'AMD64') {
    Die "unsupported CPU '$arch'. Only a 64-bit x86 build is published; there is no ARM64 build yet."
}

if ($env:NKO_VERSION) {
    $base = "https://github.com/$repo/releases/download/$($env:NKO_VERSION)"
} else {
    $base = "https://github.com/$repo/releases/latest/download"
}
if ($env:NKO_BASE_URL) { $base = $env:NKO_BASE_URL }

$binDir  = Join-Path $env:LOCALAPPDATA 'Programs\neverKickOff'
$exe     = Join-Path $binDir 'neverkickoff.exe'
$cfg     = Join-Path $binDir 'config.json'

$tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("nko-" + [System.Guid]::NewGuid().ToString('N'))

try {
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null

    # --- 1. download ------------------------------------------------------
    Say "platform : $target"
    Say "download : $base/$asset"
    try {
        (New-Object System.Net.WebClient).DownloadFile("$base/$asset", "$tmp\$asset")
        (New-Object System.Net.WebClient).DownloadFile("$base/SHA256SUMS", "$tmp\SHA256SUMS")
    } catch {
        Die "download failed: $($_.Exception.Message)
         Nothing is published until a v* tag is pushed; see .github/workflows/release.yml."
    }

    # --- 2. verify --------------------------------------------------------
    $line = Get-Content "$tmp\SHA256SUMS" |
        Where-Object { ($_ -split '\s+')[1] -eq $asset } |
        Select-Object -First 1
    if (-not $line) { Die "SHA256SUMS has no entry for $asset." }
    $expected = ($line -split '\s+')[0].ToLower()
    $actual   = (Get-FileHash "$tmp\$asset" -Algorithm SHA256).Hash.ToLower()
    if ($expected -ne $actual) { Die "checksum mismatch for $asset." }
    Say "checksum : ok"

    # --- 3. install -------------------------------------------------------
    Expand-Archive -Path "$tmp\$asset" -DestinationPath "$tmp\x" -Force
    $unpacked = Join-Path $tmp "x\neverkickoff-$target"
    if (-not (Test-Path (Join-Path $unpacked 'neverkickoff.exe'))) {
        Die "unexpected archive layout (no neverkickoff.exe)."
    }

    New-Item -ItemType Directory -Force -Path $binDir | Out-Null
    if (Test-Path $exe) { Say "note     : replacing the existing $exe." }
    Copy-Item (Join-Path $unpacked 'neverkickoff.exe') $exe -Force

    # With no path argument the app reads config.json from next to the
    # executable, so the default ships beside it - but never clobber edits.
    if (-not (Test-Path $cfg)) {
        Copy-Item (Join-Path $unpacked 'config.json') $cfg -Force
    }

    $version = & $exe --version
    if ($LASTEXITCODE -ne 0) { Die "the installed binary would not run." }
    Say "installed: $exe ($version)"

    # --- 4. put it on the user PATH ---------------------------------------
    # A `neverkickoff.cmd` from the Python installer may sit in the same folder.
    # That is fine: PATHEXT lists .EXE before .CMD, so this binary wins.
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

    # --- 5. report --------------------------------------------------------
    Write-Host ""
    Write-Host "neverKickOff installed."
    Write-Host "  binary : $exe"
    Write-Host "  config : $cfg"
    Write-Host "  run    : neverkickoff          (in a NEW terminal; with no argument it uses that config)"
    if ($pathAdded) {
        Write-Host ""
        Write-Host "Added $binDir to your PATH - open a new terminal for it to apply."
    }
} finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
