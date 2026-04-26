"""
JARVIS Skill — Note Taking
Save and read back voice notes.
"""
import os
from datetime import datetime
from pathlib import Path
from jarvis.config import CONFIG, ROOT_DIR
from jarvis.skills.base import BaseSkill


class NotesSkill(BaseSkill):
    name = "notes"
    priority = 12

    _TAKE_TRIGGERS = ["take a note", "note this", "write this down", "jot down", "save a note", "add a note"]
    _READ_TRIGGERS = ["read my notes", "show my notes", "what are my notes", "read notes"]
    _CLEAR_TRIGGERS = ["clear my notes", "delete all notes"]

    def __init__(self, memory=None):
        super().__init__(memory)
        cfg = CONFIG.get("skills", {}).get("notes", {})
        self.notes_dir = ROOT_DIR / cfg.get("notes_dir", "data/notes")
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.notes_file = self.notes_dir / "notes.txt"

    def can_handle(self, text: str) -> bool:
        return self._contains_any(text, self._TAKE_TRIGGERS + self._READ_TRIGGERS + self._CLEAR_TRIGGERS)

    def execute(self, text: str) -> str:
        text_lower = text.lower()

        if self._contains_any(text_lower, self._READ_TRIGGERS):
            if not self.notes_file.exists() or self.notes_file.stat().st_size == 0:
                return "You have no notes saved, Sir."
            notes = self.notes_file.read_text(encoding="utf-8").strip()
            lines = notes.split("\n")
            recent = lines[-10:]  # last 10 lines
            return "Here are your recent notes, Sir:\n" + "\n".join(recent)

        if self._contains_any(text_lower, self._CLEAR_TRIGGERS):
            if self.notes_file.exists():
                self.notes_file.write_text("", encoding="utf-8")
            return "All notes cleared, Sir."

        # Take a note
        note_content = text
        for trigger in self._TAKE_TRIGGERS:
            if trigger in text_lower:
                idx = text_lower.index(trigger) + len(trigger)
                note_content = text[idx:].strip().lstrip(":,-").strip()
                break

        if not note_content:
            return "What would you like me to note down, Sir?"

        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M]")
        line = f"{timestamp} {note_content}\n"
        with open(self.notes_file, "a", encoding="utf-8") as f:
            f.write(line)

        return f"Note saved, Sir: \"{note_content}\""

    def execute_action(self, action: str, params: dict) -> str:
        if action == "take_note":
            content = params.get("content", params.get("_raw", ""))
            if not content:
                return "What would you like me to note down, Sir?"
            from datetime import datetime as dt
            timestamp = dt.now().strftime("[%Y-%m-%d %H:%M]")
            line = f"{timestamp} {content}\n"
            with open(self.notes_file, "a", encoding="utf-8") as f:
                f.write(line)
            return f'Note saved, Sir: "{content}"'
        elif action == "read_notes":
            if not self.notes_file.exists() or self.notes_file.stat().st_size == 0:
                return "You have no notes saved, Sir."
            notes = self.notes_file.read_text(encoding="utf-8").strip()
            lines = notes.split("\n")
            recent = lines[-10:]
            return "Here are your recent notes, Sir:\n" + "\n".join(recent)
        return self.execute(params.get("_raw", ""))

