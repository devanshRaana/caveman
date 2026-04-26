"""
JARVIS Skill — Date & Time
"""
from datetime import datetime
from jarvis.skills.base import BaseSkill


class DateTimeSkill(BaseSkill):
    name = "datetime"
    priority = 10  # Very fast, check early

    _TRIGGERS = [
        "what time", "what's the time", "current time",
        "what day", "what date", "today's date", "what year",
        "day is it", "date is it", "time is it",
    ]

    def can_handle(self, text: str) -> bool:
        return self._contains_any(text, self._TRIGGERS)

    def execute(self, text: str) -> str:
        now = datetime.now()
        text_lower = text.lower()
        if any(w in text_lower for w in ["time", "hour", "clock"]):
            return f"The current time is {now.strftime('%I:%M %p')}, Sir."
        elif any(w in text_lower for w in ["date", "day", "today"]):
            return f"Today is {now.strftime('%A, %B %d, %Y')}, Sir."
        else:
            return f"It is {now.strftime('%A, %B %d, %Y at %I:%M %p')}, Sir."

    def execute_action(self, action: str, params: dict) -> str:
        raw = params.get("_raw", params.get("query", "time"))
        return self.execute(raw)

