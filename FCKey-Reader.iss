#define AppName "FCKey Reader"
#define AppVersion "1.0.0"
#define AppExe "FCKey-Reader.exe"

[Setup]
AppId={{E7A4D6A2-9D8D-4D3D-9B5A-7D2C8B4F1001}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=AllenShiina-Mashiiro
DefaultDirName={autopf}\FCKey Reader
DefaultGroupName={#AppName}
OutputDir=dist
OutputBaseFilename=FCKey-Reader-Setup
ArchitecturesInstallIn64BitMode=x64
ChangesAssociations=yes
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加快捷方式："; Flags: unchecked

[Files]
Source: "dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
Root: HKCR; Subkey: ".fckey"; ValueType: string; ValueName: ""; ValueData: "FCKeyReader.Metadata"; Flags: uninsdeletevalue
Root: HKCR; Subkey: ".fckey\OpenWithProgids"; ValueType: string; ValueName: "FCKeyReader.Metadata"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCR; Subkey: "FCKeyReader.Metadata"; ValueType: string; ValueName: ""; ValueData: "Fake-Compression key metadata"; Flags: uninsdeletekey
Root: HKCR; Subkey: "FCKeyReader.Metadata\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExe},0"
Root: HKCR; Subkey: "FCKeyReader.Metadata\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""
