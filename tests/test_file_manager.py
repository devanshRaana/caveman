"""
Tests for JARVIS V2 — File Manager Skill
Tests create, read, edit, delete, and open file operations.
"""
import os
import sys
import tempfile
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from jarvis.skills.file_manager import FileManagerSkill


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory(prefix="jarvis_test_") as td:
        yield td


@pytest.fixture
def skill(temp_dir):
    """Create FileManagerSkill with temp directory as default."""
    s = FileManagerSkill()
    s.default_dir = Path(temp_dir)
    return s


class TestFileCreate:
    def test_create_simple_file(self, skill, temp_dir):
        result = skill.execute_action("file_create", {
            "filename": "test.txt",
            "content": "Hello World"
        })
        assert "created" in result.lower()
        filepath = Path(temp_dir) / "test.txt"
        assert filepath.exists()
        assert filepath.read_text() == "Hello World"

    def test_create_todo_list(self, skill, temp_dir):
        result = skill.execute_action("file_create", {
            "filename": "todo.txt",
            "content": "Buy groceries\nPick up laundry\nCall mom"
        })
        assert "created" in result.lower()
        assert "3 lines" in result

    def test_create_file_auto_extension(self, skill, temp_dir):
        result = skill.execute_action("file_create", {
            "filename": "notes",
            "content": ""
        })
        filepath = Path(temp_dir) / "notes.txt"
        assert filepath.exists()

    def test_create_duplicate_warns(self, skill, temp_dir):
        skill.execute_action("file_create", {"filename": "dup.txt", "content": ""})
        result = skill.execute_action("file_create", {"filename": "dup.txt", "content": ""})
        assert "already exists" in result.lower()

    def test_create_no_filename_returns_error(self, skill):
        result = skill.execute_action("file_create", {"content": "data"})
        assert "need" in result.lower() or "filename" in result.lower()


class TestFileRead:
    def test_read_existing_file(self, skill, temp_dir):
        filepath = Path(temp_dir) / "readable.txt"
        filepath.write_text("Line 1\nLine 2\nLine 3")
        result = skill.execute_action("file_read", {"filename": "readable.txt"})
        assert "Line 1" in result
        assert "Line 3" in result

    def test_read_empty_file(self, skill, temp_dir):
        filepath = Path(temp_dir) / "empty.txt"
        filepath.write_text("")
        result = skill.execute_action("file_read", {"filename": "empty.txt"})
        assert "empty" in result.lower()

    def test_read_nonexistent_file(self, skill):
        result = skill.execute_action("file_read", {"filename": "nope.txt"})
        assert "doesn't exist" in result.lower() or "couldn't find" in result.lower()


class TestFileEdit:
    def test_add_lines(self, skill, temp_dir):
        filepath = Path(temp_dir) / "editable.txt"
        filepath.write_text("Item 1")
        result = skill.execute_action("file_edit", {
            "filename": "editable.txt",
            "add_lines": ["Item 2", "Item 3"]
        })
        assert "added" in result.lower() or "2 item" in result.lower()
        content = filepath.read_text()
        assert "Item 2" in content
        assert "Item 3" in content

    def test_remove_lines(self, skill, temp_dir):
        filepath = Path(temp_dir) / "removable.txt"
        filepath.write_text("Keep this\nRemove this\nKeep this too")
        result = skill.execute_action("file_edit", {
            "filename": "removable.txt",
            "remove_lines": ["Remove this"]
        })
        assert "removed" in result.lower()
        content = filepath.read_text()
        assert "Remove this" not in content
        assert "Keep this" in content

    def test_edit_creates_if_missing(self, skill, temp_dir):
        result = skill.execute_action("file_edit", {
            "filename": "newedit.txt",
            "add_lines": ["First line"]
        })
        filepath = Path(temp_dir) / "newedit.txt"
        assert filepath.exists()


class TestFileDelete:
    def test_delete_existing(self, skill, temp_dir):
        filepath = Path(temp_dir) / "deleteme.txt"
        filepath.write_text("temp")
        result = skill.execute_action("file_delete", {"filename": "deleteme.txt"})
        assert "deleted" in result.lower()
        assert not filepath.exists()

    def test_delete_nonexistent(self, skill):
        result = skill.execute_action("file_delete", {"filename": "ghost.txt"})
        assert "doesn't exist" in result.lower()


class TestFileOpen:
    def test_open_nonexistent_warns(self, skill):
        result = skill.execute_action("file_open", {"filename": "nope.txt"})
        assert "couldn't find" in result.lower()


class TestChainContext:
    def test_filename_from_context(self, skill, temp_dir):
        """Test that file operations can use filename from chain context."""
        filepath = Path(temp_dir) / "chained.txt"
        filepath.write_text("Original content")
        result = skill.execute_action("file_read", {
            "filename": "",
            "_chain_context": {"last_filename": "chained.txt"}
        })
        assert "Original content" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
