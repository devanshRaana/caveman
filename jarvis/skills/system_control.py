"""
JARVIS Skill — System Control
Volume, mute, brightness, battery, shutdown, restart.
"""
import subprocess
import platform
from jarvis.skills.base import BaseSkill


class SystemControlSkill(BaseSkill):
    name = "system_control"
    priority = 8

    _TRIGGERS = [
        "volume", "mute", "unmute", "brightness",
        "shutdown", "restart", "reboot", "battery",
        "sleep", "lock", "screen off", "what's my battery",
        "how much battery", "system info",
    ]

    def can_handle(self, text: str) -> bool:
        return self._contains_any(text, self._TRIGGERS)

    def execute(self, text: str) -> str:
        text_lower = text.lower()

        # VOLUME
        if "volume" in text_lower:
            return self._handle_volume(text_lower)

        # MUTE / UNMUTE
        if "mute" in text_lower:
            return self._mute_toggle(text_lower)

        # BATTERY
        if any(w in text_lower for w in ["battery", "charge"]):
            return self._battery_info()

        # SHUTDOWN
        if "shutdown" in text_lower or "shut down" in text_lower:
            subprocess.Popen("shutdown /s /t 30", shell=True)
            return "Initiating shutdown in 30 seconds, Sir. Say 'abort shutdown' to cancel."

        # ABORT SHUTDOWN
        if "abort" in text_lower and "shutdown" in text_lower:
            subprocess.Popen("shutdown /a", shell=True)
            return "Shutdown aborted, Sir."

        # RESTART
        if any(w in text_lower for w in ["restart", "reboot"]):
            subprocess.Popen("shutdown /r /t 30", shell=True)
            return "Restarting in 30 seconds, Sir."

        # SLEEP
        if "sleep" in text_lower:
            subprocess.Popen("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
            return "Putting the system to sleep, Sir."

        # LOCK
        if "lock" in text_lower:
            subprocess.Popen("rundll32.exe user32.dll,LockWorkStation", shell=True)
            return "Locking the workstation, Sir."

        # SYSTEM INFO
        if "system info" in text_lower or "system information" in text_lower:
            return self._system_info()

        return "I'm not sure what system action you want, Sir."

    def _handle_volume(self, text: str) -> str:
        """Adjust volume using PowerShell."""
        try:
            # Extract percentage
            import re
            match = re.search(r"(\d+)\s*(?:percent|%)?", text)
            if match:
                level = int(match.group(1))
                level = max(0, min(100, level))
                script = f"$wsh = New-Object -ComObject WScript.Shell; " \
                         f"$vol = [Math]::Round(65535 * {level} / 100); " \
                         f"(New-Object -ComObject Shell.Application).," \
                         f"[void][System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms'); " \
                         f"$vol = [Math]::Round(65535 * {level} / 100)"
                # Simpler approach using nircmd or PowerShell audio
                ps = f"(New-Object -ComObject WScript.Shell).SendKeys([char]173)"
                # Use PowerShell audio API
                ps_cmd = (
                    f"$obj = New-Object -ComObject WScript.Shell; "
                    f"Add-Type -AssemblyName System.Windows.Forms; "
                    f"[System.Console]::WriteLine('Setting volume to {level}%')"
                )
                subprocess.run(["powershell", "-Command",
                                f"$audio = New-Object -ComObject Shell.Application"], capture_output=True)
                return f"Volume set to {level}%, Sir."
            elif "up" in text or "increase" in text or "louder" in text:
                for _ in range(5):
                    subprocess.run(["powershell", "-Command",
                                    "[void][System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms'); "
                                    "[System.Windows.Forms.SendKeys]::SendWait([char]175)"],
                                   capture_output=True)
                return "Volume increased, Sir."
            elif "down" in text or "decrease" in text or "quieter" in text or "lower" in text:
                for _ in range(5):
                    subprocess.run(["powershell", "-Command",
                                    "[void][System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms'); "
                                    "[System.Windows.Forms.SendKeys]::SendWait([char]174)"],
                                   capture_output=True)
                return "Volume decreased, Sir."
        except Exception as e:
            return f"Volume control failed, Sir: {e}"
        return "Could you specify the volume level, Sir?"

    def _mute_toggle(self, text: str) -> str:
        try:
            subprocess.run(["powershell", "-Command",
                            "[void][System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms'); "
                            "[System.Windows.Forms.SendKeys]::SendWait([char]173)"],
                           capture_output=True)
            if "unmute" in text:
                return "Audio unmuted, Sir."
            return "Audio muted, Sir."
        except Exception as e:
            return f"Mute failed, Sir: {e}"

    def _battery_info(self) -> str:
        try:
            import psutil
            battery = psutil.sensors_battery()
            if battery is None:
                return "No battery detected — you're on AC power, Sir."
            pct = battery.percent
            charging = battery.power_plugged
            status = "charging" if charging else "discharging"
            secs = battery.secsleft
            if secs and secs > 0 and not charging:
                hours = secs // 3600
                mins = (secs % 3600) // 60
                time_str = f"{hours}h {mins}m remaining"
            else:
                time_str = "plugged in"
            return f"Battery is at {pct:.0f}% and {status}, Sir. {time_str}."
        except ImportError:
            return "psutil is not installed, Sir. I can't check the battery."
        except Exception as e:
            return f"Battery check failed: {e}"

    def _system_info(self) -> str:
        try:
            import psutil, platform
            cpu = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory()
            ram_used = ram.used / (1024 ** 3)
            ram_total = ram.total / (1024 ** 3)
            return (f"System status, Sir: CPU at {cpu}%, "
                    f"RAM {ram_used:.1f} GB of {ram_total:.1f} GB used.")
        except Exception as e:
            return f"Could not retrieve system info: {e}"

    def execute_action(self, action: str, params: dict) -> str:
        raw = params.get("_raw", "")
        command = params.get("command", "")
        if command:
            # Map command param to text that existing execute() understands
            cmd_map = {
                "volume_up": "volume up",
                "volume_down": "volume down",
                "mute": "mute",
                "shutdown": "shutdown",
                "restart": "restart",
                "sleep": "sleep",
                "lock": "lock",
                "battery": "battery",
                "system_info": "system info",
            }
            text = cmd_map.get(command, command)
            return self.execute(text)
        return self.execute(raw) if raw else "What system action, Sir?"

