; PH-LW-11: pinned Inno Setup 6.7.4. No UAC/PATH/firewall/ExecutionPolicy changes.
#define BuildId "@BUILD_ID@"
[Setup]
AppId=ProjectHarnessLocalWeb
AppName=Project Harness Local Web
AppVersion=0.1.0-dev
AppVerName=Project Harness {#BuildId} (unsigned WIP)
DefaultDirName={localappdata}\Programs\ProjectHarness
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.22000
CreateAppDir=yes
DisableProgramGroupPage=yes
DisableDirPage=no
UninstallFilesDir={app}\uninstall
OutputDir=@OUTPUT@
OutputBaseFilename=Harness-Setup-win-x64
Compression=lzma2
SolidCompression=yes
CloseApplications=no
AppMutex=Local\ProjectHarnessLocalWeb
RestartApplications=no
UninstallDisplayIcon={app}\versions\{#BuildId}\Harness.exe
SetupLogging=yes

[Files]
Source: "@BUNDLE@\*"; DestDir: "{tmp}\payload"; Flags: dontcopy recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\Project Harness"; Filename: "{app}\versions\{#BuildId}\Harness.exe"; WorkingDir: "{app}"
Name: "{userdesktop}\Project Harness"; Filename: "{app}\versions\{#BuildId}\Harness.exe"; WorkingDir: "{app}"

[Run]
Filename: "{app}\versions\{#BuildId}\Harness.exe"; Description: "Открыть Project Harness"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
#include "payload_uninstall.iss"

[Code]
procedure ActivatePayload;
var Code: Integer;
begin
#include "payload_checks.iss"
  if not Exec(ExpandConstant('{tmp}\payload\Harness.exe'), '--install-payload "' + ExpandConstant('{app}') + '"', ExpandConstant('{tmp}'), SW_HIDE, ewWaitUntilTerminated, Code) then
    RaiseException('Cannot start verified installation helper');
  if Code <> 0 then RaiseException('Installation refused: destination ownership, space, integrity or permissions. Existing version and projects preserved. Re-run setup after correcting the cause.');
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  try
    ExtractTemporaryFiles('{tmp}\payload\*');
    ActivatePayload;
  except
    Result := GetExceptionMessage;
  end;
end;

function InitializeUninstall: Boolean;
begin
  Result := True;
  if not UninstallSilent then
    MsgBox('Удаляется только комплект приложения. Проекты, approvals и app-data сохранены. Для полного удаления приватных данных отдельно удалите %LOCALAPPDATA%\ProjectHarness и ProjectHarness-workspaces после резервного копирования. Папки проектов не удаляются.', mbInformation, MB_OK);
end;
