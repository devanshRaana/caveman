"""
JARVIS — Startup Entry Point (.pyw = no console window)
This file is called by Task Scheduler on login.
Starts JARVIS with tray icon in the background.
"""
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from jarvis.tray import start_tray_thread
from main import JARVIS
from jarvis.audio.tts import TextToSpeech

# Start tray icon
start_tray_thread()

# Start JARVIS
jarvis = JARVIS()
jarvis.run()
