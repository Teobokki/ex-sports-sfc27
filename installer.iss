#define MyVer "1.0.0"
[Setup]
AppId={{B3C5E2A1-7D4F-4E61-9A27-5F0C8D2E1B27}
AppName=EX SPORTS SFC 27 STANDARD EDITION
AppVersion={#MyVer}
AppVerName=EX SPORTS SFC 27 STANDARD EDITION {#MyVer}
AppPublisher=EX Inc./HYPERION DIGITAL
AppPublisherURL=https://github.com/Teobokki/ex-sports-sfc27
AppCopyright=©2026 EX Inc./HYPERION DIGITAL ©2026
VersionInfoVersion={#MyVer}
VersionInfoCompany=EX Inc./HYPERION DIGITAL
VersionInfoCopyright=©2026 EX Inc./HYPERION DIGITAL ©2026
VersionInfoProductName=EX SPORTS SFC 27 STANDARD EDITION
VersionInfoDescription=EX SPORTS SFC 27 STANDARD EDITION Setup
DefaultDirName={localappdata}\Programs\EX SPORTS SFC 27
DefaultGroupName=EX SPORTS SFC 27
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=EX-SPORTS-SFC27-Setup-{#MyVer}
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\EX SPORTS SFC 27.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "dist\EX SPORTS SFC 27\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\EX SPORTS SFC 27"; Filename: "{app}\EX SPORTS SFC 27.exe"; IconFilename: "{app}\EX SPORTS SFC 27.exe"
Name: "{group}\Uninstall EX SPORTS SFC 27"; Filename: "{uninstallexe}"
Name: "{userdesktop}\EX SPORTS SFC 27"; Filename: "{app}\EX SPORTS SFC 27.exe"; IconFilename: "{app}\EX SPORTS SFC 27.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\EX SPORTS SFC 27.exe"; Description: "Launch EX SPORTS SFC 27 now"; Flags: nowait postinstall skipifsilent
