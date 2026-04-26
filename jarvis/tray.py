"""
JARVIS — System Tray Icon
Runs JARVIS as a Windows system tray application.
Right-click menu: Status / Open Logs / Quit
"""
import sys
import threading
import subprocess
from pathlib import Path

try:
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False


ROOT_DIR = Path(__file__).parent


def create_icon_image(color="cyan"):
    """Create a simple circular JARVIS icon."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Outer circle (JARVIS blue)
    draw.ellipse([4, 4, size - 4, size - 4], fill=(0, 200, 255, 255))
    # Inner 'J' letter — simple bars
    draw.rectangle([26, 16, 36, 44], fill=(0, 0, 0, 255))
    draw.rectangle([16, 44, 36, 52], fill=(0, 0, 0, 255))
    return img


def open_logs():
    log_file = ROOT_DIR / "logs" / "jarvis.log"
    subprocess.Popen(["notepad.exe", str(log_file)], shell=True)


def quit_jarvis(icon, item):
    icon.stop()
    sys.exit(0)


def run_tray(jarvis_instance=None):
    if not TRAY_AVAILABLE:
        return

    icon_image = create_icon_image()
    menu = pystray.Menu(
        item("JARVIS — Online", lambda: None, enabled=False),
        item("Open Logs", lambda icon, item: open_logs()),
        item("Quit", quit_jarvis),
    )
    icon = pystray.Icon("JARVIS", icon_image, "JARVIS — Online", menu)
    icon.run()


def start_tray_thread(jarvis_instance=None):
    """Launch tray icon in a background daemon thread."""
    t = threading.Thread(target=run_tray, args=(jarvis_instance,), daemon=True)
    t.start()
    return t
