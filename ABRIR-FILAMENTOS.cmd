@echo off
start "Filamento K2" /min pythonw "%~dp0server.py"
ping 127.0.0.1 -n 2 >nul
start "" "http://127.0.0.1:8765/"

