"""
JARVIS — Windows Auto-Boot Setup
Registers JARVIS to start automatically when Windows boots.
Adds a Windows Registry entry under HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run.

Run this script ONCE to enable auto-start:
    python setup_autostart.py

Run with --remove to disable auto-start:
    python setup_autostart.py --remove
"""
import sys
import os
import winreg
from pathlib import Path

JARVIS_DIR = Path(__file__).parent.resolve()
REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
REGISTRY_NAME = "JARVIS"


def get_python_path():
    """Get the path to pythonw.exe (windowless Python)."""
    python_dir = Path(sys.executable).parent
    pythonw = python_dir / "pythonw.exe"
    if pythonw.exists():
        return str(pythonw)
    # Fallback to regular python
    return sys.executable


def enable_autostart():
    """Register JARVIS to start on Windows boot."""
    python = get_python_path()
    startup_script = JARVIS_DIR / "jarvis_startup.pyw"

    # Create the startup script if it doesn't exist
    if not startup_script.exists():
        startup_script.write_text(
            f'"""JARVIS Auto-Start Script — runs silently on boot."""\n'
            f'import subprocess\n'
            f'import sys\n'
            f'import os\n'
            f'import time\n'
            f'\n'
            f'JARVIS_DIR = r"{JARVIS_DIR}"\n'
            f'\n'
            f'# Wait a few seconds for system to fully boot\n'
            f'time.sleep(10)\n'
            f'\n'
            f'# Start Ollama server if not running\n'
            f'try:\n'
            f'    subprocess.Popen(\n'
            f'        ["ollama", "serve"],\n'
            f'        stdout=subprocess.DEVNULL,\n'
            f'        stderr=subprocess.DEVNULL,\n'
            f'        creationflags=subprocess.CREATE_NO_WINDOW\n'
            f'    )\n'
            f'    time.sleep(5)  # Give Ollama time to start\n'
            f'except Exception:\n'
            f'    pass\n'
            f'\n'
            f'# Start JARVIS\n'
            f'os.chdir(JARVIS_DIR)\n'
            f'subprocess.Popen(\n'
            f'    [sys.executable, "main.py"],\n'
            f'    cwd=JARVIS_DIR,\n'
            f'    creationflags=subprocess.CREATE_NEW_CONSOLE\n'
            f')\n',
            encoding="utf-8"
        )

    # Command to run on startup
    command = f'"{python}" "{startup_script}"'

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REGISTRY_KEY,
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, REGISTRY_NAME, 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)
        print(f"[OK] JARVIS registered for auto-start on boot!")
        print(f"     Command: {command}")
        print(f"\n     JARVIS will now start automatically every time you open your laptop.")
        print(f"     Run 'python setup_autostart.py --remove' to disable.")
    except Exception as e:
        print(f"[ERROR] Failed to set registry entry: {e}")
        print("        Try running as Administrator.")


def disable_autostart():
    """Remove JARVIS from Windows auto-start."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REGISTRY_KEY,
            0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, REGISTRY_NAME)
        winreg.CloseKey(key)
        print("[OK] JARVIS auto-start disabled.")
    except FileNotFoundError:
        print("[INFO] JARVIS was not registered for auto-start.")
    except Exception as e:
        print(f"[ERROR] Failed to remove registry entry: {e}")


if __name__ == "__main__":
    if "--remove" in sys.argv or "--disable" in sys.argv:
        disable_autostart()
    else:
        enable_autostart()
