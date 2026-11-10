# PH-LW-05 native Windows acceptance. No inline Python or stderr-as-failure heuristic.
[CmdletBinding()]
param(
  [string]$PythonExecutable = 'py',
  [string]$PythonVersion = '',
  [Parameter(Mandatory = $true)][string]$DocumentationZip,
  [string]$LogDirectory = '',
  [switch]$SkipRegressions
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $LogDirectory) { $LogDirectory = Join-Path $PSScriptRoot 'windows_ci_logs/PH_LW_05' }
$pythonArgs = @()
if ($PythonVersion) { $pythonArgs += $PythonVersion }
elseif ([IO.Path]::GetFileNameWithoutExtension($PythonExecutable) -eq 'py') { $pythonArgs += '-3.14' }
$pythonArgs += @((Join-Path $PSScriptRoot 'run_windows_acceptance.py'), '--stage', '05',
    '--documentation-zip', $DocumentationZip, '--log-dir', $LogDirectory)
if ($SkipRegressions) { $pythonArgs += '--skip-regressions' }
# Windows PowerShell 5.1 wraps native stderr in NativeCommandError, even on exit 0.
# The Python runner records exact exits and structured unittest skip/failure counts.
$previousPreference = $ErrorActionPreference
try {
  $ErrorActionPreference = 'Continue'
  & $PythonExecutable @pythonArgs
  $resultCode = $LASTEXITCODE
} finally { $ErrorActionPreference = $previousPreference }
exit $resultCode
