"""
JARVIS Skill — Utility Tools
Handles timers, stopwatches, reminders, and basic math calculations.
Runs asynchronous background threads for alarms that can interrupt sleep mode.
"""
import time
import threading
from typing import Optional, Callable
from jarvis.skills.base import BaseSkill
from jarvis.logger import logger


class ToolsSkill(BaseSkill):
    name = "tools"
    priority = 5

    def __init__(self, memory=None, tts_callback: Optional[Callable[[str], None]] = None):
        super().__init__(memory)
        self.tts_callback = tts_callback
        
        # Track active timers/stopwatches
        self.stopwatches = {}  # name -> start_time
        
    def can_handle(self, text: str) -> bool:
        triggers = [
            "set a timer", "timer for", "remind me", "start stopwatch", 
            "stop stopwatch", "calculate", "what is", "math"
        ]
        return self._contains_any(text, triggers)

    def execute(self, text: str) -> str:
        # Legacy fallback if IntentRouter fails
        return "The tools skill requires structured intent routing."

    def execute_action(self, action: str, params: dict) -> str:
        handler = {
            "set_timer": self._set_timer,
            "set_reminder": self._set_reminder,
            "stopwatch_start": self._stopwatch_start,
            "stopwatch_stop": self._stopwatch_stop,
            "calculate": self._calculate,
        }.get(action)

        if handler:
            return handler(params)
        return f"Unknown tools action: {action}"

    def _parse_duration(self, duration_str: str) -> int:
        """Parse a duration string (e.g., '10 minutes', '1 hour 30 seconds') into seconds."""
        duration_str = duration_str.lower()
        total_seconds = 0
        
        # Simple extraction
        words = duration_str.split()
        for i, word in enumerate(words):
            if word.isdigit():
                val = int(word)
                if i + 1 < len(words):
                    unit = words[i+1]
                    if "hour" in unit:
                        total_seconds += val * 3600
                    elif "minute" in unit or "min" in unit:
                        total_seconds += val * 60
                    elif "second" in unit or "sec" in unit:
                        total_seconds += val
        
        # Fallback if no units parsed but numbers exist
        if total_seconds == 0:
            import re
            nums = re.findall(r'\d+', duration_str)
            if nums:
                # Default to minutes if just a number is given
                total_seconds = int(nums[0]) * 60

        return total_seconds

    def _async_alarm(self, seconds: int, message: str, is_reminder: bool = False):
        """Sleeps in a background thread and then fires the TTS callback."""
        logger.info(f"ToolsSkill: Starting background alarm for {seconds}s ({message})")
        time.sleep(seconds)
        
        alert_text = f"Sir, your timer is up!"
        if is_reminder and message:
            alert_text = f"Sir, I am reminding you: {message}"
        elif message and message.lower() not in ["timer", ""]:
            alert_text = f"Sir, your timer for {message} is up!"
            
        logger.info(f"ToolsSkill: Alarm ringing: {alert_text}")
        
        if self.tts_callback:
            self.tts_callback(alert_text)
        else:
            logger.warning("ToolsSkill: No TTS callback defined. Cannot speak alarm!")

    def _set_timer(self, params: dict) -> str:
        duration_str = params.get("duration", "")
        name = params.get("name", "")
        
        if not duration_str:
            return "How long should I set the timer for, Sir?"
            
        seconds = self._parse_duration(duration_str)
        if seconds <= 0:
            return f"I couldn't understand the duration '{duration_str}', Sir."
            
        # Start background thread
        t = threading.Thread(
            target=self._async_alarm, 
            args=(seconds, name, False),
            daemon=True
        )
        t.start()
        
        resp = f"I've set a timer for {duration_str}"
        if name:
            resp += f" called '{name}'"
        return resp + ", Sir."

    def _set_reminder(self, params: dict) -> str:
        duration_str = params.get("duration", "")
        task = params.get("task", "")
        
        if not duration_str or not task:
            return "I need both a time and a task for the reminder, Sir."
            
        seconds = self._parse_duration(duration_str)
        if seconds <= 0:
            # Maybe the LLM gave a specific time "at 5 PM". 
            # For this V1, we only handle relative durations like "in 10 minutes".
            return "I can currently only set reminders relative to now, like 'in 10 minutes', Sir."
            
        # Start background thread
        t = threading.Thread(
            target=self._async_alarm, 
            args=(seconds, task, True),
            daemon=True
        )
        t.start()
        
        return f"I will remind you to '{task}' in {duration_str}, Sir."

    def _stopwatch_start(self, params: dict) -> str:
        name = params.get("name", "default")
        self.stopwatches[name] = time.time()
        return "Stopwatch started, Sir."

    def _stopwatch_stop(self, params: dict) -> str:
        name = params.get("name", "default")
        
        # If default wasn't found but there's EXACTLY one active stopwatch, stop that one.
        if name not in self.stopwatches and len(self.stopwatches) == 1:
            name = list(self.stopwatches.keys())[0]
            
        if name not in self.stopwatches:
            return "You don't have a stopwatch running right now, Sir."
            
        start_t = self.stopwatches.pop(name)
        elapsed = int(time.time() - start_t)
        
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        seconds = elapsed % 60
        
        parts = []
        if hours > 0: parts.append(f"{hours} hours")
        if minutes > 0: parts.append(f"{minutes} minutes")
        if seconds > 0 or not parts: parts.append(f"{seconds} seconds")
        
        return f"Stopwatch stopped at {', '.join(parts)}, Sir."

    def _calculate(self, params: dict) -> str:
        expression = params.get("expression", "")
        if not expression:
            return "What would you like me to calculate, Sir?"
            
        # Clean expression
        allowed_chars = "0123456789+-*/() .%"
        clean_expr = "".join(c for c in expression.replace("x", "*").replace("X", "*").replace("times", "*") if c in allowed_chars)
        
        try:
            # Safe eval of math
            result = eval(clean_expr, {"__builtins__": None}, {})
            
            # Format nicely
            if isinstance(result, float) and result.is_integer():
                result = int(result)
            elif isinstance(result, float):
                result = round(result, 4)
                
            return f"The answer to {expression} is {result}, Sir."
        except Exception:
            return f"I couldn't calculate that math expression: '{expression}', Sir."
