"""
JARVIS Skill — Memory (Remember / Recall)
"""
import re
from jarvis.skills.base import BaseSkill


class MemorySkill(BaseSkill):
    name = "memory"
    priority = 5  # Highest priority — explicit user intent

    _REMEMBER_TRIGGERS = ["remember", "don't forget", "note that", "keep in mind", "store this"]
    _RECALL_TRIGGERS = ["what do you know about", "do you remember", "recall", "what did i tell you about"]
    _FORGET_TRIGGERS = ["forget", "delete memory", "remove memory"]
    _LIST_TRIGGERS = ["list my memories", "what do you remember", "show memories", "all memories"]

    def can_handle(self, text: str) -> bool:
        return self._contains_any(text, self._REMEMBER_TRIGGERS + self._RECALL_TRIGGERS +
                                  self._FORGET_TRIGGERS + self._LIST_TRIGGERS)

    def execute(self, text: str) -> str:
        text_lower = text.lower()

        # LIST all memories
        if self._contains_any(text_lower, self._LIST_TRIGGERS):
            if not self.memory:
                return "Memory system is not available, Sir."
            mems = self.memory.list_all()
            if not mems:
                return "Your memory vault is empty, Sir."
            lines = [f"{i+1}. {m['content']}" for i, m in enumerate(mems[:10])]
            return "Here's what I remember, Sir:\n" + "\n".join(lines)

        # REMEMBER something
        if self._contains_any(text_lower, self._REMEMBER_TRIGGERS):
            # Extract what to remember: text after the trigger phrase
            content = text
            for trigger in self._REMEMBER_TRIGGERS:
                if trigger in text_lower:
                    idx = text_lower.index(trigger) + len(trigger)
                    content = text[idx:].strip().lstrip(":, that").strip()
                    break
            if not content:
                return "What would you like me to remember, Sir?"
            if self.memory:
                self.memory.remember(content)
            return f"Noted, Sir. I'll remember that: \"{content}\""

        # RECALL something
        if self._contains_any(text_lower, self._RECALL_TRIGGERS):
            if not self.memory:
                return "Memory system unavailable, Sir."
            query = text
            for trigger in self._RECALL_TRIGGERS:
                if trigger in text_lower:
                    idx = text_lower.index(trigger) + len(trigger)
                    query = text[idx:].strip()
                    break
            results = self.memory.recall(query, n_results=3)
            if not results:
                return f"I don't have anything stored about that, Sir."
            return f"Here's what I remember about that, Sir:\n{results}"

        return "I'm not sure what you'd like me to remember, Sir."

    def execute_action(self, action: str, params: dict) -> str:
        if action == "remember":
            fact = params.get("fact", params.get("_raw", ""))
            if not fact:
                return "What would you like me to remember, Sir?"
            if self.memory:
                self.memory.remember(fact)
            return f'Noted, Sir. I\'ll remember that: "{fact}"'
        elif action == "recall":
            query = params.get("query", params.get("_raw", ""))
            if not self.memory:
                return "Memory system unavailable, Sir."
            results = self.memory.recall(query, n_results=3)
            if not results:
                return "I don't have anything stored about that, Sir."
            return f"Here's what I remember about that, Sir:\n{results}"
        return self.execute(params.get("_raw", ""))

