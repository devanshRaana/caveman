"""
Tests for JARVIS V2 — Intent Router
Tests LLM parsing fallback (keyword-based) and JSON extraction.
"""
import sys
import json
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from jarvis.brain.intent_router import IntentRouter


@pytest.fixture
def router():
    """Create IntentRouter (LLM will not be available in test env)."""
    r = IntentRouter()
    r._client = None  # Force fallback mode for testing
    return r


class TestFallbackParsing:
    """Test keyword-based fallback when LLM is unavailable."""

    def test_file_create(self, router):
        result = router.parse("create a file called shopping list")
        assert result["action"] == "file_create"

    def test_todo_create(self, router):
        result = router.parse("create a to-do list")
        assert result["action"] == "file_create"

    def test_file_edit(self, router):
        result = router.parse("add to my shopping list buy milk")
        assert result["action"] == "file_edit"

    def test_file_delete(self, router):
        result = router.parse("delete file notes.txt")
        assert result["action"] == "file_delete"

    def test_open_app(self, router):
        result = router.parse("open chrome")
        assert result["action"] == "open_app"

    def test_close_app(self, router):
        result = router.parse("close notepad")
        assert result["action"] == "close_app"

    def test_web_search(self, router):
        result = router.parse("search for python tutorials")
        assert result["action"] == "web_search"

    def test_send_email(self, router):
        result = router.parse("send an email to john@gmail.com")
        assert result["action"] == "send_email"

    def test_send_whatsapp(self, router):
        result = router.parse("send whatsapp message to Mom")
        assert result["action"] == "send_whatsapp"

    def test_google_meet(self, router):
        result = router.parse("start a meet call")
        assert result["action"] == "start_meet"

    def test_video_call(self, router):
        result = router.parse("video call on whatsapp")
        assert result["action"] == "start_video_call"

    def test_system_control_volume(self, router):
        result = router.parse("volume up")
        assert result["action"] == "system_control"

    def test_system_control_battery(self, router):
        result = router.parse("how much battery do I have")
        assert result["action"] == "system_control"

    def test_notes(self, router):
        result = router.parse("take a note buy groceries")
        assert result["action"] == "take_note"

    def test_read_notes(self, router):
        result = router.parse("show my notes")
        assert result["action"] == "read_notes"

    def test_datetime(self, router):
        result = router.parse("what time is it")
        assert result["action"] == "datetime"

    def test_general_chat(self, router):
        result = router.parse("tell me a joke")
        assert result["action"] == "general_chat"


class TestJsonExtraction:
    """Test JSON extraction from various LLM response formats."""

    def test_raw_json(self, router):
        text = '{"action": "file_create", "params": {"filename": "test.txt"}}'
        result = router._extract_json(text)
        parsed = json.loads(result)
        assert parsed["action"] == "file_create"

    def test_markdown_code_block(self, router):
        text = '```json\n{"action": "open_app", "params": {"app_name": "chrome"}}\n```'
        result = router._extract_json(text)
        parsed = json.loads(result)
        assert parsed["action"] == "open_app"

    def test_json_with_surrounding_text(self, router):
        text = 'Here is the action: {"action": "web_search", "params": {"query": "test"}} done.'
        result = router._extract_json(text)
        parsed = json.loads(result)
        assert parsed["action"] == "web_search"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
