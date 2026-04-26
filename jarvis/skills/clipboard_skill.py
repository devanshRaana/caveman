"""
JARVIS Skill — Clipboard Summarizer / Reader
"""
import pyperclip
from jarvis.skills.base import BaseSkill


class ClipboardSkill(BaseSkill):
    name = "clipboard"
    priority = 18

    _TRIGGERS = ["clipboard", "what's in my clipboard", "read clipboard",
                 "summarize clipboard", "paste content", "what did i copy"]

    def can_handle(self, text: str) -> bool:
        return self._contains_any(text, self._TRIGGERS)

    def execute(self, text: str) -> str:
        try:
            content = pyperclip.paste()
            if not content or not content.strip():
                return "Your clipboard is empty, Sir."
            preview = content.strip()[:300]
            if len(content) > 300:
                return (f"Your clipboard contains {len(content)} characters, Sir. "
                        f"Here's a preview: \"{preview}...\"")
            return f"Your clipboard contains: \"{preview}\""
        except Exception as e:
            return f"Couldn't access clipboard, Sir: {e}"
