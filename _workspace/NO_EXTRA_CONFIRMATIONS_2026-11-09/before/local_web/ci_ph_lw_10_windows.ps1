# PH-LW-10 native acceptance of unpacked working files; ZIP is optional.
[CmdletBinding()]
param(
  [string]$PythonExecutable = 'py',
  [string]$PythonVersion = '',
  [string]$DocumentationZip = '',
  [Parameter(Mandatory = $true)][string]$LogDirectory,
  [switch]$SkipRegressions
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$pythonArgs = @()
if ($PythonVersion) { $pythonArgs += $PythonVersion }
elseif ([IO.Path]::GetFileNameWithoutExtension($PythonExecutable) -eq 'py') { $pythonArgs += '-3.14' }
$pythonArgs += @((Join-Path $PSScriptRoot 'run_windows_acceptance.py'), '--stage', '10', '--log-dir', $LogDirectory)
if ($DocumentationZip) { $pythonArgs += @('--documentation-zip', $DocumentationZip) }
if ($SkipRegressions) { $pythonArgs += '--skip-regressions' }
$previousPreference = $ErrorActionPreference
try {
  $ErrorActionPreference = 'Continue'
  & $PythonExecutable @pythonArgs
  $resultCode = $LASTEXITCODE
} finally { $ErrorActionPreference = $previousPreference }
exit $resultCode

