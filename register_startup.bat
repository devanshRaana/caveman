@echo off
:: ============================================================
::  JARVIS — Windows Startup Registration
::  Adds JARVIS to Windows Task Scheduler so it auto-starts
::  on every login (runs hidden in background with tray icon).
:: ============================================================

SET SCRIPT_DIR=%~dp0
SET PYTHON_EXE=python
SET JARVIS_MAIN=%SCRIPT_DIR%jarvis_startup.pyw

echo [JARVIS Setup] Registering JARVIS in Task Scheduler...

schtasks /create ^
  /tn "JARVIS_AI_Assistant" ^
  /tr "\"%PYTHON_EXE%\" \"%JARVIS_MAIN%\"" ^
  /sc ONLOGON ^
  /rl HIGHEST ^
  /f

IF %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] JARVIS will now start automatically on every login.
) ELSE (
    echo [ERROR] Task Scheduler registration failed. Try running as Administrator.
)
pause
