param([string]$ShortcutName = "RL-MEC Dashboard", [switch]$AllUsers)

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VbsPath = Join-Path $ProjectRoot "start_dashboard.vbs"

if (!(Test-Path $VbsPath)) {
    throw "start_dashboard.vbs not found: $VbsPath"
}

if ($AllUsers) {
    $ProgramsDir = Join-Path $env:ProgramData "Microsoft\Windows\Start Menu\Programs"
} else {
    $ProgramsDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
}

$ShortcutDir = Join-Path $ProgramsDir "RL-MEC Dashboard"
$ShortcutPath = Join-Path $ShortcutDir "$ShortcutName.lnk"

New-Item -ItemType Directory -Force -Path $ShortcutDir | Out-Null

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = Join-Path $env:WINDIR "System32\wscript.exe"
$Shortcut.Arguments = "`"$VbsPath`""
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.Description = "Launch RL-MEC Dashboard"
$Shortcut.Save()

Write-Host "Created Start Menu shortcut: $ShortcutPath"
