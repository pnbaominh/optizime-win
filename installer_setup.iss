; =====================================================================
; Script tạo bộ cài đặt tiêu chuẩn chuyên nghiệp bằng Inno Setup (OBS-Style)
; Dành cho Windows Deep Optimizer
; =====================================================================

#define MyAppName "Windows Deep Optimizer"
#define MyAppVersion "1.1.3"
#define MyAppPublisher "Bim"
#define MyAppURL "https://github.com/pnbaominh/optizime-win"
#define MyAppExeName "WindowsDeepOptimizer.exe"

[Setup]
AppId={{9F57B7B8-356C-4B1A-98C3-08D3893FA22E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=WindowsDeepOptimizer_Setup
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
AppMutex=WindowsDeepOptimizerMutex
CloseApplications=yes
RestartApplications=yes
SetupIconFile=assets\app.ico
UninstallDisplayIcon={app}\assets\app.ico
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\assets\app.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent runascurrentuser

[Code]
function SetEnvVarNull(lpName: String; lpValue: LongInt): BOOL;
external 'SetEnvironmentVariableW@kernel32.dll stdcall';

function SetEnvVarStr(lpName: String; lpValue: String): BOOL;
external 'SetEnvironmentVariableW@kernel32.dll stdcall';

function InitializeSetup(): Boolean;
begin
  // Xoa triet de cac bien moi truong PyInstaller ke thua tu tien trinh cu
  SetEnvVarNull('_PYI_PARENT_PID', 0);
  SetEnvVarNull('_MEIPASS2', 0);
  SetEnvVarNull('_PYI_APPLICATION_HOME_DIR', 0);
  SetEnvVarNull('_PYI_SPLASH_IPC', 0);
  SetEnvVarStr('PYINSTALLER_RESET_ENVIRONMENT', '1');
  Result := True;
end;
