# Windows-only PH-LW-01 contract/source baseline; NOT a Windows acceptance by merely existing.
# Launch on real Windows 11 x64, NTFS: pwsh -NoProfile -File .\local_web\ci_ph_lw_01_windows.ps1 -DocumentZip C:\absolute\docs.zip
[CmdletBinding()]
param(
    [string]$PythonExecutable = 'py',
    [string]$PythonVersion = '-3.14',
    [Parameter(Mandatory = $true)][string]$DocumentZip
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$engine = (Resolve-Path (Join-Path $here '..')).Path
$docRoot = Join-Path $engine 'docs\Project_Harness_Documentation_v0.5.1'
$logRoot = Join-Path $engine 'local_web\windows_ci_logs'
if ($env:OS -ne 'Windows_NT') { throw 'NOT RUN: this entrypoint MUST execute on real Windows 11 x64 NTFS.' }
if ([Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString() -ne 'X64') { throw 'Unsupported architecture: require x64' }
if ([Environment]::OSVersion.Version.Build -lt 22000) { throw 'Unsupported Windows build: require Windows 11 >= 22000' }
$rootPath = [System.IO.Path]::GetPathRoot($engine)
$driveLetter = $rootPath.Substring(0, 1)
$volume = Get-Volume -DriveLetter $driveLetter -ErrorAction Stop
if ($volume.FileSystem -ne 'NTFS') { throw 'NOT RUN: source test drive must be NTFS' }
if (-not (Test-Path -LiteralPath $DocumentZip -PathType Leaf)) { throw "Missing exact Documentation ZIP: $DocumentZip" }
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
$summary = Join-Path $logRoot 'RUN_SUMMARY.txt'
'PH-LW-01 native Windows CI; real platform, not simulated' | Set-Content -LiteralPath $summary -Encoding UTF8
"Windows: $([Environment]::OSVersion.Version); Drive: $driveLetter NTFS; Python invocation: $PythonExecutable $PythonVersion" | Add-Content -LiteralPath $summary
function RunPython([string]$Name, [string[]]$Arguments) {
    $outfile = Join-Path $logRoot "$Name.log"
    # PowerShell argument array invokes executable directly: no user-supplied shell expression.
    & $PythonExecutable $PythonVersion @Arguments 2>&1 | Tee-Object -FilePath $outfile
    $status = $LASTEXITCODE
    "$Name exit=$status" | Add-Content -LiteralPath $summary
    if ($status -ne 0) { throw "$Name failed exit=$status; see $outfile" }
}
Push-Location -LiteralPath $engine
$oldPyPath = $env:PYTHONPATH
try {
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $env:PYTHONPATH = "$engine\src;$engine"
    RunPython 'platform_import' @('-c', 'import sys,platform,project_harness,project_harness.cli; assert sys.platform=="win32"; print(platform.platform()); print("IMPORT_OK")')
    RunPython 'targeted_contract' @('-m', 'unittest', '-v', 'tests.test_ph_lw_01_contract')
    RunPython 'full_regression' @('tests/run_tests.py')
    RunPython 'distribution_doctor' @('project-harness.py', 'doctor')
    $report = Join-Path $logRoot 'DOC_VALIDATOR.json'
    RunPython 'docs_integrity' @('docs/Project_Harness_Documentation_v0.5.1/tools/validate_documentation.py', $docRoot, '--zip', $DocumentZip, '--json', $report)
    'WINDOWS_IMPORT_SOURCE_AND_UNIT: PASS; see logs; no browser/installer acceptance.' | Add-Content -LiteralPath $summary
    'BROWSER_REAL_E2E: NOT RUN (PH-LW-04..12)' | Add-Content -LiteralPath $summary
    'FROZEN_INSTALLER_NON_ADMIN: NOT RUN (PH-LW-11/12)' | Add-Content -LiteralPath $summary
    'ROOTLESS_PODMAN_SECURITY: NOT RUN / AUTOMATIC_EXECUTOR NO-GO' | Add-Content -LiteralPath $summary
    Write-Host "Source/contract Windows baseline PASS (not Web acceptance): $summary"
} finally {
    $env:PYTHONPATH = $oldPyPath
    Pop-Location
}
