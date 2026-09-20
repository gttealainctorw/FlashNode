; FlashNode Windows installer (Inno Setup 6).
;
; Build order:  python -m PyInstaller FlashNode.spec   ->  dist\FlashNode\
;               ISCC installer.iss                     ->  release\FlashNode_Setup_<version>.exe
; (tools\build_release.py runs both and writes SHA256SUMS.txt.)
;
; The version is NOT typed here: it is read from the executable's version resource,
; which PyInstaller fills from version.json. version.json is the single source of truth.

#define MyAppName "FlashNode"
#define MyAppExeName "FlashNode.exe"
#define MyAppPublisher "CARLOS ALAIN MARTINEZ AGUILAR"
#define MyAppDir SourcePath + "\dist\FlashNode"
#define MyAppVersion GetStringFileInfo(MyAppDir + "\" + MyAppExeName, "ProductVersion")

[Setup]
; Constant AppId = upgrades replace the existing installation instead of creating a second one.
AppId={{6D70F270-B17A-47E3-A78A-C3967E1F24B2}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
; Per-user install by default (no administrator rights, no UAC prompt): %LOCALAPPDATA%\Programs\FlashNode.
; Administrators are offered an all-users install into Program Files.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=release
OutputBaseFilename=FlashNode_Setup_{#MyAppVersion}
SetupIconFile=assets\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Ask to close a running FlashNode before upgrading instead of failing on locked files.
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[InstallDelete]
; PyInstaller one-folder layout: remove the previous version's runtime completely so no stale
; module or DLL from an older release survives an upgrade.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#MyAppDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

; User data (downloaded firmware cache) lives in %LOCALAPPDATA%\FlashNode and is deliberately
; left in place on uninstall; it is small and safe to delete by hand.
