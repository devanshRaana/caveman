"""
JARVIS V2.2 — Live System Verification Script
Tests ALL skills against the REAL system.

What this script does:
1. Creates a test file on Desktop
2. Reads it back
3. Adds content to it
4. Creates a test folder
5. Opens Chrome (tests browser)
6. Opens YouTube search in Chrome
7. Tests intent router with various commands
8. Cleans up test files

Run:  python tests/verify_live.py
"""
import sys
import os
import time
import tempfile
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from jarvis.skills.file_manager import FileManagerSkill
from jarvis.skills.browser_skill import BrowserSkill
from jarvis.brain.intent_router import IntentRouter
from jarvis.skills.registry import SkillRegistry


def green(text): return f"\033[92m[OK] {text}\033[0m"
def red(text): return f"\033[91m[FAIL] {text}\033[0m"
def yellow(text): return f"\033[93m[WARN] {text}\033[0m"
def blue(text): return f"\033[94m[TEST] {text}\033[0m"


class LiveVerifier:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.test_dir = Path.home() / "Desktop" / "JARVIS_TEST"

    def check(self, name, condition, msg=""):
        if condition:
            print(green(f"{name}: {msg or 'OK'}"))
            self.passed += 1
        else:
            print(red(f"{name}: {msg or 'FAILED'}"))
            self.failed += 1

    def warn(self, name, msg):
        print(yellow(f"{name}: {msg}"))
        self.warnings += 1

    def test_file_create(self, fm):
        """Test: Create a file on Desktop."""
        print(blue("Testing file creation..."))
        result = fm.execute_action("file_create", {
            "filename": "jarvis_test.txt",
            "content": "Hello from JARVIS!\nThis is a test file.",
            "directory": str(self.test_dir),
        })
        filepath = self.test_dir / "jarvis_test.txt"
        self.check("File Create", filepath.exists(), result)

    def test_file_read(self, fm):
        """Test: Read the file back."""
        print(blue("Testing file read..."))
        result = fm.execute_action("file_read", {
            "filename": "jarvis_test.txt",
            "directory": str(self.test_dir),
        })
        self.check("File Read", "Hello from JARVIS" in result, result[:80])

    def test_file_edit(self, fm):
        """Test: Add lines to file."""
        print(blue("Testing file edit (add lines)..."))
        result = fm.execute_action("file_edit", {
            "filename": "jarvis_test.txt",
            "add_lines": ["Buy groceries", "Call Mom"],
            "directory": str(self.test_dir),
        })
        filepath = self.test_dir / "jarvis_test.txt"
        content = filepath.read_text() if filepath.exists() else ""
        self.check("File Edit", "Buy groceries" in content, result)

    def test_folder_create(self, fm):
        """Test: Create a folder."""
        print(blue("Testing folder creation..."))
        result = fm.execute_action("folder_create", {
            "folder_name": "TestSubFolder",
            "directory": str(self.test_dir),
        })
        folder = self.test_dir / "TestSubFolder"
        self.check("Folder Create", folder.exists() and folder.is_dir(), result)

    def test_file_delete(self, fm):
        """Test: Delete a file."""
        print(blue("Testing file delete..."))
        result = fm.execute_action("file_delete", {
            "filename": "jarvis_test.txt",
            "directory": str(self.test_dir),
        })
        filepath = self.test_dir / "jarvis_test.txt"
        self.check("File Delete", not filepath.exists(), result)

    def test_chrome_open(self, browser):
        """Test: Open Chrome with a URL."""
        print(blue("Testing Chrome open..."))
        result = browser.execute_action("open_url", {"url": "https://www.google.com"})
        self.check("Chrome Open (Google)", "opening" in result.lower() or "chrome" in result.lower(), result)
        time.sleep(2)

    def test_youtube_search(self, browser):
        """Test: YouTube search in Chrome."""
        print(blue("Testing YouTube search..."))
        result = browser.execute_action("youtube_search", {"query": "how to code in python"})
        self.check("YouTube Search", "searching youtube" in result.lower() or "youtube" in result.lower(), result)
        time.sleep(2)

    def test_intent_router(self, router):
        """Test: Intent router parses various commands correctly."""
        print(blue("Testing intent router..."))
        tests = [
            ("create a file called shopping list", "file_create"),
            ("open chrome", "open_app"),
            ("search youtube for python tutorials", "youtube_search"),
            ("create a folder called projects", "folder_create"),
            ("open downloads folder", "folder_open"),
            ("send email to test@gmail.com", "send_email"),
            ("send a whatsapp message to Mom", "send_whatsapp"),
            ("search for machine learning", "web_search"),
            ("what time is it", "datetime"),
            ("tell me a joke", "general_chat"),
        ]
        for cmd, expected_action in tests:
            result = router.parse(cmd)
            actual = result.get("action", "")
            self.check(f"Intent: '{cmd[:40]}'", actual == expected_action,
                       f"expected={expected_action}, got={actual}")

    def cleanup(self):
        """Remove test directory."""
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)
            print(blue("Cleaned up test directory."))

    def run(self):
        print("=" * 60)
        print("  [*] JARVIS V2.2 -- Live System Verification")
        print("=" * 60)

        # Create test dir
        self.test_dir.mkdir(parents=True, exist_ok=True)

        # Init skills
        fm = FileManagerSkill()
        fm.default_dir = self.test_dir
        browser = BrowserSkill()
        router = IntentRouter()
        router._client = None  # Force fallback for consistency

        print("\n--- File Operations ---")
        self.test_file_create(fm)
        self.test_file_read(fm)
        self.test_file_edit(fm)
        self.test_folder_create(fm)
        self.test_file_delete(fm)

        print("\n--- Browser Operations ---")
        self.test_chrome_open(browser)
        self.test_youtube_search(browser)

        print("\n--- Intent Router ---")
        self.test_intent_router(router)

        print("\n--- Cleanup ---")
        self.cleanup()

        print("\n" + "=" * 60)
        print(f"  Results: {self.passed} passed, {self.failed} failed, {self.warnings} warnings")
        print("=" * 60)

        if self.failed == 0:
            print(green("ALL TESTS PASSED! JARVIS is fully operational."))
        else:
            print(red(f"{self.failed} tests failed. Check the output above."))

        return self.failed == 0


if __name__ == "__main__":
    verifier = LiveVerifier()
    success = verifier.run()
    sys.exit(0 if success else 1)
