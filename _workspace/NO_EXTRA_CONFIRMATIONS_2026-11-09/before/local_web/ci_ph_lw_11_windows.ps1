# Source acceptance only. Installed EXE acceptance has a separate runner/output.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$PythonExecutable,
  [Parameter(Mandatory=$true)][string]$LogDirectory
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$logPath = [IO.Path]::GetFullPath($LogDirectory)
if (Test-Path -LiteralPath $logPath) { throw 'Use a new log directory' }
New-Item -ItemType Directory -Path $logPath | Out-Null
& $PythonExecutable (Join-Path $PSScriptRoot 'run_windows_acceptance.py') --stage 10 --log-dir (Join-Path $logPath 'previous') --skip-regressions
$previousExit = $LASTEXITCODE
$enginePath = Split-Path $PSScriptRoot -Parent
$env:PYTHONPATH = (Join-Path $enginePath 'src') + ';' + $enginePath
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
& $PythonExecutable -B -m unittest -v tests.test_ph_lw_11_desktop *> (Join-Path $logPath 'desktop.log')
$desktopExit = $LASTEXITCODE
@{stage='PH-LW-11'; previous_exit=$previousExit; desktop_exit=$desktopExit; installer='Separate actual installer run required'; automatic_executor='NO-GO'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $logPath 'PH_LW_11_NATIVE.json') -Encoding utf8
if ($previousExit -ne 0 -or $desktopExit -ne 0) { exit 1 }
exit 0
