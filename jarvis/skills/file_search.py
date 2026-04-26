"""
JARVIS Skill — File Search
Voice-controlled local file searching.
"""
import os
import subprocess
from pathlib import Path
from jarvis.config import CONFIG
from jarvis.skills.base import BaseSkill


class FileSearchSkill(BaseSkill):
    name = "file_search"
    priority = 20

    _TRIGGERS = ["find file", "search for file", "where is", "locate file",
                 "find the file", "search file", "look for file"]

    def __init__(self, memory=None):
        super().__init__(memory)
        cfg = CONFIG.get("skills", {}).get("file_search", {})
        self.search_roots = cfg.get("search_roots", ["C:/Users"])

    def can_handle(self, text: str) -> bool:
        return self._contains_any(text, self._TRIGGERS)

    def execute(self, text: str) -> str:
        text_lower = text.lower()
        # Extract filename query
        query = text
        for trigger in self._TRIGGERS:
            if trigger in text_lower:
                idx = text_lower.index(trigger) + len(trigger)
                query = text[idx:].strip().lstrip(":,-").strip()
                break

        if not query:
            return "What file are you looking for, Sir?"

        # Remove common filler words
        for word in ["called", "named", "for", "the", "a"]:
            query = query.replace(f" {word} ", " ").strip()

        results = []
        try:
            for root in self.search_roots:
                for dirpath, dirnames, filenames in os.walk(root):
                    # Skip system/hidden dirs
                    dirnames[:] = [d for d in dirnames
                                   if not d.startswith(".") and d not in
                                   ["Windows", "System32", "Program Files", "$Recycle.Bin",
                                    "AppData", "ProgramData", "node_modules"]]
                    for fname in filenames:
                        if query.lower() in fname.lower():
                            results.append(os.path.join(dirpath, fname))
                            if len(results) >= 5:
                                break
                    if len(results) >= 5:
                        break
        except PermissionError:
            pass
        except Exception as e:
            return f"File search error, Sir: {e}"

        if not results:
            return f"I couldn't find any file matching '{query}', Sir."

        response = f"Found {len(results)} file(s) matching '{query}', Sir:\n"
        for r in results[:5]:
            response += f"  - {r}\n"
        return response.strip()
