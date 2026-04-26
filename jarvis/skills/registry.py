"""
JARVIS Skills — Registry V2
Routes structured actions from IntentRouter to the correct skill.
Also maintains legacy text-based routing as fallback.
"""
from typing import Optional
from jarvis.skills.base import BaseSkill
from jarvis.skills.datetime_skill import DateTimeSkill
from jarvis.skills.memory_skill import MemorySkill
from jarvis.skills.app_launcher import AppLauncherSkill
from jarvis.skills.notes_skill import NotesSkill
from jarvis.skills.system_control import SystemControlSkill
from jarvis.skills.file_search import FileSearchSkill
from jarvis.skills.clipboard_skill import ClipboardSkill
from jarvis.skills.file_manager import FileManagerSkill
from jarvis.skills.web_search import WebSearchSkill
from jarvis.skills.browser_skill import BrowserSkill
from jarvis.skills.code_execution import CodeExecutionSkill
from jarvis.logger import logger


class SkillRegistry:
    """
    V2 Skill Registry — supports both:
      1. Action-based routing (from IntentRouter)
      2. Legacy text-based routing (fallback)
    """

    def __init__(self, memory=None, tts_callback=None):
        self.memory = memory

        # Instantiate all skills
        self.file_manager = FileManagerSkill(memory=memory)
        self.browser = BrowserSkill(memory=memory)
        self.web_search = WebSearchSkill(memory=memory)
        self.app_launcher = AppLauncherSkill(memory=memory)
        self.system_control = SystemControlSkill(memory=memory)
        self.notes = NotesSkill(memory=memory)
        self.datetime_skill = DateTimeSkill(memory=memory)
        self.memory_skill = MemorySkill(memory=memory)
        self.file_search = FileSearchSkill(memory=memory)
        self.clipboard = ClipboardSkill(memory=memory)
        self.code_execution = CodeExecutionSkill(memory=memory)
        from jarvis.skills.tools import ToolsSkill
        self.tools_skill = ToolsSkill(memory=memory, tts_callback=tts_callback)

        # Legacy skills list (sorted by priority)
        self.skills: list[BaseSkill] = sorted([
            self.tools_skill,
            self.datetime_skill,
            self.memory_skill,
            self.system_control,
            self.app_launcher,
            self.notes,
            self.file_search,
            self.clipboard,
            self.code_execution,
            self.file_manager,
            self.web_search,
            self.browser,
        ], key=lambda s: s.priority)

        # Action → skill mapping for direct dispatch
        self._action_map = {
            # File operations
            "file_create": self.file_manager,
            "file_read": self.file_manager,
            "file_edit": self.file_manager,
            "file_delete": self.file_manager,
            "file_open": self.file_manager,
            "folder_create": self.file_manager,
            "folder_open": self.file_manager,
            # App control
            "open_app": self.app_launcher,
            "close_app": self.app_launcher,
            # Web / Browser
            "web_search": self.web_search,
            "send_email": self.browser,
            "send_whatsapp": self.browser,
            "start_meet": self.browser,
            "start_video_call": self.browser,
            "open_url": self.browser,
            "youtube_search": self.browser,
            # System
            "system_control": self.system_control,
            # Notes
            "take_note": self.notes,
            "read_notes": self.notes,
            # Memory
            "remember": self.memory_skill,
            "recall": self.memory_skill,
            # DateTime
            "datetime": self.datetime_skill,
            # Spotify
            "play_spotify": self.app_launcher,
            # Tools & Timers
            "set_timer": self.tools_skill,
            "set_reminder": self.tools_skill,
            "stopwatch_start": self.tools_skill,
            "stopwatch_stop": self.tools_skill,
            "calculate": self.tools_skill,
            "execute_code": self.code_execution,
        }

        logger.info(f"SkillRegistry V2 loaded: {[s.name for s in self.skills]}")

    def execute_action(self, action_dict: dict) -> Optional[str]:
        """
        Execute a structured action dict from IntentRouter.
        
        Args:
            action_dict: {"action": "file_create", "params": {...}}
            
        Returns:
            Response string, or None if action is 'general_chat'
        """
        action = action_dict.get("action", "")
        params = action_dict.get("params", {})

        if action == "general_chat":
            return None  # Let the LLM handle it

        skill = self._action_map.get(action)
        if not skill:
            logger.warning(f"SkillRegistry: No skill for action '{action}'")
            return None  # Unknown action — let LLM handle it

        try:
            # Use action-based execution if skill supports it
            if hasattr(skill, "execute_action"):
                result = skill.execute_action(action, params)
            else:
                # Fallback to legacy text execution
                raw_text = params.get("_raw", str(params))
                result = skill.execute(raw_text)

            logger.info(f"SkillRegistry: action '{action}' -> {skill.name}")
            return result

        except Exception as e:
            logger.error(f"SkillRegistry: action '{action}' failed: {e}")
            return f"I encountered an error executing that command, Sir: {e}"

    def route(self, text: str) -> Optional[str]:
        """
        Legacy text-based routing (backward compatibility).
        Returns the skill's response string if handled,
        or None if no skill matched (LLM should answer).
        """
        text_stripped = text.strip()
        if not text_stripped:
            return None

        for skill in self.skills:
            try:
                if skill.can_handle(text_stripped):
                    logger.info(f"Skill matched: [{skill.name}] for input: '{text_stripped[:50]}'")
                    return skill.execute(text_stripped)
            except Exception as e:
                logger.error(f"Skill '{skill.name}' threw an error: {e}")

        return None  # No skill handled it — let the LLM respond

    def cleanup(self):
        """Clean up resources (e.g., browser driver)."""
        if hasattr(self.browser, 'cleanup'):
            self.browser.cleanup()
