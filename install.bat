@echo off
:: ============================================================
::  JARVIS — One-Click Installer
::  Run this once and JARVIS will be fully set up.
:: ============================================================
TITLE JARVIS Installer

echo.
echo  ================================================
echo    J.A.R.V.I.S — Local Assistant Installer
echo  ================================================
echo.

:: Step 1 — Check Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found. Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)
echo [OK] Python found.

:: Step 2 — Create virtual environment
echo.
echo [1/5] Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

:: Step 3 — Upgrade pip
echo.
echo [2/5] Upgrading pip...
python -m pip install --upgrade pip --quiet

:: Step 4 — Install Python dependencies
echo.
echo [3/5] Installing Python dependencies (this may take a few minutes)...
pip install -r requirements.txt --quiet
IF %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Some packages may have failed. Continuing...
)

:: Step 5 — Download Whisper model (base)
echo.
echo [4/5] Pre-downloading Whisper 'base' model...
python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')" 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Whisper model download skipped (will download on first use).
)

:: Step 6 — Check Ollama
echo.
echo [5/5] Checking Ollama installation...
ollama --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ACTION REQUIRED] Ollama is NOT installed.
    echo  Please download it from: https://ollama.ai/download
    echo  After installing, run:  ollama pull mistral
    echo.
) ELSE (
    echo [OK] Ollama found.
    echo [Pulling Mistral model - this downloads ~4GB, please wait...]
    ollama pull mistral
)

echo.
echo  ================================================
echo    Installation Complete!
echo  ================================================
echo.
echo  To START JARVIS (with console):
echo    venv\Scripts\activate.bat ^&^& python main.py
echo.
echo  To ADD JARVIS to Windows startup (auto-boot):
echo    Run register_startup.bat as Administrator
echo.
pause
