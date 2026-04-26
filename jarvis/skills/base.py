"""
JARVIS Skills — Base Skill Class
All skills inherit from BaseSkill and implement:
  - can_handle(text) -> bool
  - execute(text, context) -> str
"""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jarvis.memory.manager import MemoryManager


class BaseSkill(ABC):
    """
    Abstract base class for all JARVIS skills.
    Skills are hot-evaluated: the first skill whose can_handle()
    returns True gets to execute for a given utterance.
    """
    name: str = "base"
    priority: int = 50  # Lower number = checked first

    def __init__(self, memory: "MemoryManager" = None):
        self.memory = memory

    @abstractmethod
    def can_handle(self, text: str) -> bool:
        """Return True if this skill should handle the user's text."""
        ...

    @abstractmethod
    def execute(self, text: str) -> str:
        """Execute the skill and return a response string."""
        ...

    def _contains_any(self, text: str, keywords: list[str]) -> bool:
        """Utility: check if any keyword appears in text."""
        text_lower = text.lower()
        return any(kw in text_lower for kw in keywords)
