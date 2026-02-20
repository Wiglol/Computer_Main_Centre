' Create_Shortcut.vbs
' -------------------
' Run this ONCE to create a global Ctrl+Alt+C hotkey that opens CMC from anywhere.
' It creates a shortcut in your Start Menu so the hotkey works system-wide.
'
' How to use:
'   Double-click  Create_Shortcut.vbs  once.
'   Done — press Ctrl+Alt+C from anywhere to launch CMC.
'
' To remove: delete the shortcut from:
'   %AppData%\Microsoft\Windows\Start Menu\Programs\CMC.lnk

Set shell = CreateObject("WScript.Shell")
Set fso   = CreateObject("Scripting.FileSystemObject")

' ── Locate Start_CMC.vbs (in same folder as this script) ──────────────────
scriptFolder = fso.GetParentFolderName(WScript.ScriptFullName)
vbsTarget    = scriptFolder & "\Start_CMC.vbs"

If Not fso.FileExists(vbsTarget) Then
    MsgBox "ERROR: Could not find Start_CMC.vbs next to this script." & vbCrLf & _
           "Expected: " & vbsTarget, vbCritical, "CMC Shortcut Creator"
    WScript.Quit 1
End If

' ── Pick a nice icon (use Python's icon if available, otherwise shell32) ───
iconPath = ""
Dim pyPaths(4)
pyPaths(0) = shell.ExpandEnvironmentStrings("%LocalAppData%") & "\Programs\Python\Python312\python.exe"
pyPaths(1) = shell.ExpandEnvironmentStrings("%LocalAppData%") & "\Programs\Python\Python311\python.exe"
pyPaths(2) = shell.ExpandEnvironmentStrings("%LocalAppData%") & "\Programs\Python\Python310\python.exe"
pyPaths(3) = "C:\Python312\python.exe"
pyPaths(4) = "C:\Python311\python.exe"

Dim i
For i = 0 To 4
    If fso.FileExists(pyPaths(i)) Then
        iconPath = pyPaths(i) & ",0"
        Exit For
    End If
Next

If iconPath = "" Then
    ' Fallback: terminal icon from shell32
    iconPath = "shell32.dll,2"
End If

' ── Create shortcut in Start Menu ─────────────────────────────────────────
startMenu = shell.ExpandEnvironmentStrings("%AppData%") & "\Microsoft\Windows\Start Menu\Programs"
shortcutPath = startMenu & "\CMC.lnk"

Set lnk = shell.CreateShortcut(shortcutPath)
lnk.TargetPath       = "wscript.exe"
lnk.Arguments        = """" & vbsTarget & """"
lnk.WorkingDirectory = scriptFolder
lnk.WindowStyle      = 1
lnk.Hotkey           = "Ctrl+Alt+C"
lnk.Description      = "Computer Main Centre"
lnk.IconLocation     = iconPath
lnk.Save

' ── Done ──────────────────────────────────────────────────────────────────
MsgBox "CMC shortcut created!" & vbCrLf & vbCrLf & _
       "Press  Ctrl+Alt+C  from anywhere to open CMC." & vbCrLf & vbCrLf & _
       "Shortcut saved to:" & vbCrLf & shortcutPath, _
       vbInformation, "CMC Shortcut Created"
