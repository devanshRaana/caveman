"""
Tests for JARVIS V2 — Command Chain Engine
Tests sequential execution, context passing, and error handling.
"""
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from jarvis.brain.command_chain import CommandChain


@pytest.fixture
def mock_skills():
    """Create a mock SkillRegistry."""
    registry = MagicMock()
    registry.execute_action = MagicMock(side_effect=lambda action: f"Done: {action.get('action', 'unknown')}")
    return registry


@pytest.fixture
def chain(mock_skills):
    """Create CommandChain with mocks."""
    return CommandChain(mock_skills, speak_fn=MagicMock())


class TestCommandChain:
    def test_empty_chain(self, chain):
        result = chain.execute([])
        assert "No commands" in result

    def test_single_step(self, chain, mock_skills):
        steps = [{"action": "file_create", "params": {"filename": "test.txt"}}]
        result = chain.execute(steps)
        mock_skills.execute_action.assert_called_once()
        assert "Done" in result

    def test_multi_step_execution(self, chain, mock_skills):
        steps = [
            {"action": "file_create", "params": {"filename": "test.txt"}},
            {"action": "file_edit", "params": {"filename": "test.txt", "add_lines": ["hello"]}},
            {"action": "file_open", "params": {"filename": "test.txt"}},
        ]
        result = chain.execute(steps)
        assert mock_skills.execute_action.call_count == 3
        assert "Step 1" in result
        assert "Step 2" in result
        assert "Step 3" in result

    def test_context_passing(self, chain, mock_skills):
        """Verify that chain context is injected into subsequent steps."""
        steps = [
            {"action": "file_create", "params": {"filename": "data.txt"}},
            {"action": "file_read", "params": {}},
        ]
        chain.execute(steps)

        # Second call should have _chain_context with info from first step
        second_call = mock_skills.execute_action.call_args_list[1]
        action_dict = second_call[0][0]
        assert "_chain_context" in action_dict["params"]
        ctx = action_dict["params"]["_chain_context"]
        assert "step_1_action" in ctx
        assert ctx["step_1_action"] == "file_create"

    def test_error_handling(self, chain, mock_skills):
        """Test that errors in one step don't stop the chain."""
        def side_effect(action):
            if action.get("action") == "bad_action":
                raise ValueError("Intentional error")
            return f"Done: {action.get('action')}"

        mock_skills.execute_action = MagicMock(side_effect=side_effect)

        steps = [
            {"action": "file_create", "params": {"filename": "test.txt"}},
            {"action": "bad_action", "params": {}},
            {"action": "file_read", "params": {"filename": "test.txt"}},
        ]
        result = chain.execute(steps)
        # All 3 steps should be attempted
        assert mock_skills.execute_action.call_count == 3
        assert "failed" in result.lower()

    def test_progress_speech(self, chain, mock_skills):
        """Test that progress updates are spoken."""
        steps = [
            {"action": "step1", "params": {}},
            {"action": "step2", "params": {}},
        ]
        chain.execute(steps)
        # speak_fn should be called for progress + completion
        assert chain.speak_fn.call_count >= 2  # "I have 2 tasks" + "step 1 complete" + "all tasks"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
