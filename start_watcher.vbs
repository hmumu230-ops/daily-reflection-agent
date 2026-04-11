Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "python """ & WshShell.ExpandEnvironmentStrings("%USERPROFILE%") & "\Desktop\每日反思智能体\sync_notes_watch.py""", 0, False
