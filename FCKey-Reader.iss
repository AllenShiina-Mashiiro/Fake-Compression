#define AppName "FCKey Reader"
#define AppVersion "1.0.0"
#define AppExe "FCKey-Reader.exe"

[Setup]
AppId={{E7A4D6A2-9D8D-4D3D-9B5A-7D2C8B4F1001}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=AllenShiina-Mashiiro
DefaultDirName={autopf}\\FCKey Reader
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=FCKey-Reader-Setup
ArchitecturesInstallIn64BitMode=x64
ChangesAssociations=yes
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："; Flags: unchecked
Name: "startmenuicon"; Description: "创建开始菜单快捷方式"; GroupDescription: "快捷方式："; Flags: unchecked

[Files]
Source: "dist\\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\\{#AppName}"; Filename: "{app}\\{#AppExe}"; Tasks: desktopicon
Name: "{group}\\{#AppName}"; Filename: "{app}\\{#AppExe}"; Tasks: startmenuicon

[Registry]
Root: HKCR; Subkey: ".fckey"; ValueType: string; ValueName: ""; ValueData: "FCKeyReader.Metadata"; Flags: uninsdeletevalue
Root: HKCR; Subkey: ".fckey\\OpenWithProgids"; ValueType: string; ValueName: "FCKeyReader.Metadata"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCR; Subkey: "FCKeyReader.Metadata"; ValueType: string; ValueName: ""; ValueData: "Fake-Compression key metadata"; Flags: uninsdeletekey
Root: HKCR; Subkey: "FCKeyReader.Metadata\\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\\{#AppExe},0"
Root: HKCR; Subkey: "FCKeyReader.Metadata\\shell\\open\\command"; ValueType: string; ValueName: ""; ValueData: """{app}\\{#AppExe}"" ""%1"""

[Run]
Filename: "{app}\\{#AppExe}"; Description: "启动 FCKey Reader"; Flags: postinstall nowait skipifsilent
