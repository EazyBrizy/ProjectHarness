# PH-LW-03 native Windows application-service check; script existing != proof of execution.
# Run in a non-admin Windows 11 x64 NTFS PowerShell using a local drive checkout:
# pwsh -NoProfile -File .\local_web\ci_ph_lw_03_windows.ps1 -DocumentationZip C:\path\Project_Harness_Documentation_v0.5.1_PH_LW_03.zip
[CmdletBinding()]
param(
    [string]$PythonExecutable = 'py',
    [string]$PythonVersion = '-3.14',
    [Parameter(Mandatory = $true)][string]$DocumentationZip
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'WINDOWS_NOT_TESTED: real native Windows is mandatory' }
if ([Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString() -ne 'X64') { throw 'Requires x64 Windows' }
if ([Environment]::OSVersion.Version.Build -lt 22000) { throw 'Requires Windows 11 >= 22000' }
$engine = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$drive = [System.IO.Path]::GetPathRoot($engine)
if ($drive -notmatch '^[a-zA-Z]:\\$') { throw 'Only local, fully-qualified drive roots are supported' }
$letter = $drive.Substring(0,1)
$volume = Get-Volume -DriveLetter $letter
if ($volume.FileSystem -ne 'NTFS') { throw 'Requires native NTFS test volume' }
if (-not (Test-Path -LiteralPath $DocumentationZip -PathType Leaf)) { throw 'Exact Documentation ZIP missing' }
$logs = Join-Path $engine 'local_web\windows_ci_logs'
New-Item -ItemType Directory -Path $logs -Force | Out-Null
$summary = Join-Path $logs 'PH_LW_03_WINDOWS_TEST_REPORT.txt'
@(
    'PH-LW-03 native Windows Local Web SERVICE tests (NOT browser/installer/Podman acceptance)',
    "Windows version: $([Environment]::OSVersion.Version)",
    "Python launcher: $PythonExecutable $PythonVersion", "Source drive: $drive NTFS"
) | Set-Content -LiteralPath $summary -Encoding UTF8
function RunHarness([string]$Name, [string[]]$Arguments) {
    $log = Join-Path $logs "$Name.log"
    & $PythonExecutable $PythonVersion @Arguments 2>&1 | Tee-Object -FilePath $log
    $rc = $LASTEXITCODE
    "$Name exit=$rc" | Add-Content -LiteralPath $summary
    if ($rc -ne 0) { throw "$Name FAILED exit=$rc; see $log" }
}
Push-Location -LiteralPath $engine
$oldPath = $env:PYTHONPATH
$oldNoByte = $env:PYTHONDONTWRITEBYTECODE
try {
    $env:PYTHONPATH = "$engine\src;$engine"
    $env:PYTHONDONTWRITEBYTECODE = '1'
    RunHarness 'win32_import_no_fcntl' @('-c', 'import sys,project_harness,project_harness.cli,project_harness.runtime; assert sys.platform=="win32"; print("NATIVE_WINDOWS_IMPORT_OK")')
    RunHarness 'ph_lw_02_windows_core' @('-m','unittest','-v','tests.test_ph_lw_02_windows_core')
    RunHarness 'ph_lw_03_application_service' @('-m','unittest','-v','tests.test_ph_lw_03_service')
    RunHarness 'distribution_doctor' @('project-harness.py','doctor')
    RunHarness 'all_regression_modules' @('tests/run_tests.py')
    $docs = Join-Path $engine 'docs\Project_Harness_Documentation_v0.5.1'
    $report = Join-Path $logs 'DOC_VALIDATION.json'
    RunHarness 'documentation_validator' @('docs/Project_Harness_Documentation_v0.5.1/tools/validate_documentation.py', $docs, '--zip', $DocumentationZip, '--json', $report)
    'WINDOWS_NATIVE_APPLICATION_SERVICE: PASS only when all commands exit=0; see this exact report' | Add-Content -LiteralPath $summary
    'WINDOWS_BROWSER_INSTALLER: NOT RUN (PH-LW-04..12)' | Add-Content -LiteralPath $summary
    'PODMAN_SECURITY_AND_APPROVED_EGRESS: NOT RUN / NO-GO' | Add-Content -LiteralPath $summary
} finally {
    $env:PYTHONPATH = $oldPath
    $env:PYTHONDONTWRITEBYTECODE = $oldNoByte
    Pop-Location
}
