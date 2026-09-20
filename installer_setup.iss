; Script tạo bộ cài đặt chuyên nghiệp bằng Inno Setup
; Dành cho Windows Deep Optimizer

[Setup]
AppId={{9F57B7B8-356C-4B1A-98C3-08D3893FA22E}
AppName=Windows Deep Optimizer
AppVersion=1.0.0
AppPublisher=Bim
DefaultDirName={autopf}\WindowsDeepOptimizer
DefaultGroupName=Windows Deep Optimizer
OutputDir=installer_output
OutputBaseFilename=WindowsDeepOptimizer_Setup_v1.0
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\WindowsDeepOptimizer.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Windows Deep Optimizer"; Filename: "{app}\WindowsDeepOptimizer.exe"
Name: "{group}\{cm:UninstallProgram,Windows Deep Optimizer}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Windows Deep Optimizer"; Filename: "{app}\WindowsDeepOptimizer.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\WindowsDeepOptimizer.exe"; Description: "{cm:LaunchProgram,Windows Deep Optimizer}"; Flags: nowait postinstall skipifsilent
