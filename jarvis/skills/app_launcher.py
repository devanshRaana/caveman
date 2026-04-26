"""
JARVIS Skill -- App Launcher V2
Opens and closes Windows applications by voice.
Supports Spotify playback, system-wide app search, and foreground launching.
"""
import subprocess
import os
import shutil
from pathlib import Path
from jarvis.skills.base import BaseSkill
from jarvis.logger import logger


class AppLauncherSkill(BaseSkill):
    name = "app_launcher"
    priority = 15

    _TRIGGERS = ["open", "launch", "start", "run"]
    _CLOSE_TRIGGERS = ["close", "quit", "kill", "shut down"]

    # Common app aliases -> how to open them
    APP_MAP = {
        "chrome": "chrome",
        "google chrome": "chrome",
        "firefox": "firefox",
        "edge": "msedge",
        "notepad": "notepad",
        "calculator": "calc",
        "file explorer": "explorer",
        "explorer": "explorer",
        "task manager": "taskmgr",
        "spotify": "spotify",
        "discord": "discord",
        "vscode": "code",
        "visual studio code": "code",
        "vs code": "code",
        "cmd": "cmd",
        "command prompt": "cmd",
        "powershell": "powershell",
        "paint": "mspaint",
        "word": "winword",
        "excel": "excel",
        "teams": "teams",
        "zoom": "zoom",
        "vlc": "vlc",
        "whatsapp": "whatsapp",
        "telegram": "telegram",
        "settings": "ms-settings:",
        "control panel": "control",
        "snipping tool": "snippingtool",
    }

    # Map for taskkill (need .exe suffix)
    KILL_MAP = {
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "firefox": "firefox.exe",
        "edge": "msedge.exe",
        "notepad": "notepad.exe",
        "spotify": "spotify.exe",
        "discord": "discord.exe",
        "vscode": "code.exe",
        "visual studio code": "code.exe",
        "teams": "teams.exe",
        "zoom": "zoom.exe",
        "vlc": "vlc.exe",
    }

    def can_handle(self, text: str) -> bool:
        return self._contains_any(text, self._TRIGGERS + self._CLOSE_TRIGGERS)

    def execute(self, text: str) -> str:
        text_lower = text.lower()

        # CLOSE app
        if self._contains_any(text_lower, self._CLOSE_TRIGGERS):
            for app_name in self.KILL_MAP:
                if app_name in text_lower:
                    exe = self.KILL_MAP[app_name]
                    try:
                        subprocess.run(["taskkill", "/f", "/im", exe],
                                       capture_output=True)
                        return f"Closing {app_name.title()}, Sir."
                    except Exception as e:
                        return f"Couldn't close {app_name.title()}: {e}"
            return "I'm not sure which application to close, Sir."

        # OPEN app
        for app_name, cmd in self.APP_MAP.items():
            if app_name in text_lower:
                return self._launch_app(app_name, cmd)

        # Try to extract unknown app name
        for trigger in self._TRIGGERS:
            if trigger in text_lower:
                idx = text_lower.index(trigger) + len(trigger)
                remaining = text[idx:].strip()
                if remaining:
                    app_guess = remaining.rstrip(".")
                    return self._launch_app(app_guess, app_guess)

        return "Which application would you like me to open, Sir?"

    def _launch_app(self, display_name: str, cmd: str) -> str:
        """Launch an app using the most reliable Windows method."""
        try:
            # Method 1: Use 'start' command (most reliable for GUI apps)
            subprocess.Popen(
                f'start "" "{cmd}"',
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            logger.info(f"AppLauncher: Opened {display_name} via 'start {cmd}'")
            return f"Opening {display_name.title()} right away, Sir."
        except Exception:
            pass

        try:
            # Method 2: Try os.startfile (works for registered apps)
            os.startfile(cmd)
            logger.info(f"AppLauncher: Opened {display_name} via os.startfile")
            return f"Opening {display_name.title()} right away, Sir."
        except Exception:
            pass

        try:
            # Method 3: Try shutil.which to find the executable
            exe_path = shutil.which(cmd) or shutil.which(f"{cmd}.exe")
            if exe_path:
                subprocess.Popen(exe_path, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
                logger.info(f"AppLauncher: Opened {display_name} via shutil.which")
                return f"Opening {display_name.title()} right away, Sir."
        except Exception:
            pass

        return f"I couldn't find '{display_name}' to open it, Sir."

    def execute_action(self, action: str, params: dict) -> str:
        app_name = params.get("app_name", "")
        if not app_name:
            raw = params.get("_raw", "")
            return self.execute(raw) if raw else "Which application, Sir?"

        if action == "close_app":
            exe = self.KILL_MAP.get(app_name.lower(), f"{app_name}.exe")
            try:
                subprocess.run(["taskkill", "/f", "/im", exe], capture_output=True)
                return f"Closing {app_name.title()}, Sir."
            except Exception as e:
                return f"Couldn't close {app_name.title()}: {e}"

        if action == "play_spotify":
            song = params.get("song_name", app_name)
            # Clean up raw text to extract just the song name
            raw = params.get("_raw", song)
            for remove in ["play", "on spotify", "spotify", "play me", "put on"]:
                raw = raw.lower().replace(remove, "").strip()
            song = raw.strip() if raw.strip() else song
            return self.play_on_spotify(song)

        # open_app
        cmd = self.APP_MAP.get(app_name.lower(), app_name)
        return self._launch_app(app_name, cmd)

    def play_on_spotify(self, song_name: str) -> str:
        """Open Spotify and search/play a song."""
        try:
            # First open Spotify
            self._launch_app("Spotify", "spotify")

            import time
            time.sleep(3)  # Wait for Spotify to open

            # Use Spotify URI search to play the song
            search_uri = f"spotify:search:{song_name}"
            os.startfile(search_uri)
            logger.info(f"AppLauncher: Playing '{song_name}' on Spotify")
            return f"Playing '{song_name}' on Spotify, Sir."
        except Exception as e:
            logger.error(f"AppLauncher: Spotify play error: {e}")
            return f"I opened Spotify, but had trouble searching for '{song_name}', Sir. You may need to search manually."
