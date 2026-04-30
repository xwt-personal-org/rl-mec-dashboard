Set WshShell = CreateObject("WScript.Shell")
Set FileSystem = CreateObject("Scripting.FileSystemObject")
ScriptDir = FileSystem.GetParentFolderName(WScript.ScriptFullName)
WshShell.Run """" & FileSystem.BuildPath(ScriptDir, "start_dashboard.bat") & """ --hidden", 0, False
Set FileSystem = Nothing
Set WshShell = Nothing
