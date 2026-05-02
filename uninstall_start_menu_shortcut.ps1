param([string]$ShortcutName = "RL-MEC Dashboard", [switch]$AllUsers)

if ($AllUsers) {
    $ProgramsDir = Join-Path $env:ProgramData "Microsoft\Windows\Start Menu\Programs"
} else {
    $ProgramsDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
}

$ShortcutDir = Join-Path $ProgramsDir "RL-MEC Dashboard"
$ShortcutPath = Join-Path $ShortcutDir "$ShortcutName.lnk"

if (Test-Path $ShortcutPath) {
    Remove-Item $ShortcutPath -Force
    Write-Host "Removed Start Menu shortcut: $ShortcutPath"
} else {
    Write-Host "Shortcut not found: $ShortcutPath"
}

if (Test-Path $ShortcutDir) {
    $Remaining = Get-ChildItem -Path $ShortcutDir -Force
    if ($Remaining.Count -eq 0) {
        Remove-Item $ShortcutDir -Force
        Write-Host "Removed empty Start Menu folder: $ShortcutDir"
    }
}
