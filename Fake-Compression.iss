#define AppName "Fake-Compression"
#define AppVersion "1.1.4-Alpha"
#define AppExe "Fake-Compression.exe"
#define KeyProgId "FakeCompression.FCKey.OpenWith"

[Setup]
AppId={{B4A2B39E-34D4-4BA1-8F4A-8B68DDE9E001}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=AllenShiina-Mashiiro
DefaultDirName={autopf}\Fake-Compression
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=Fake-Compression-Setup
SetupIconFile=build\fake-compression.ico
UninstallDisplayIcon={app}\{#AppExe}
ArchitecturesInstallIn64BitMode=x64
ChangesAssociations=yes
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "startmenuicon"; Description: "创建开始菜单快捷方式"; GroupDescription: "快捷方式："; Flags: unchecked
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："; Flags: unchecked

[Files]
Source: "dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: startmenuicon
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; 主程序仅作为 .fckey 的“打开方式”候选，不抢占 Reader 的默认打开行为。
Root: HKCR; Subkey: ".fckey\OpenWithProgids"; ValueType: string; ValueName: "{#KeyProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCR; Subkey: "{#KeyProgId}"; ValueType: string; ValueName: ""; ValueData: "Fake-Compression (FCKey helper)"; Flags: uninsdeletekey
Root: HKCR; Subkey: "{#KeyProgId}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExe},0"
Root: HKCR; Subkey: "{#KeyProgId}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""
