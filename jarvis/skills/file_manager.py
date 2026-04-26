"""
JARVIS Skill — File Manager
Create, read, edit, delete, and open files on the user's computer.
"""
import os
import subprocess
from pathlib import Path
from datetime import datetime
from jarvis.config import CONFIG, ROOT_DIR
from jarvis.skills.base import BaseSkill
from jarvis.logger import logger


class FileManagerSkill(BaseSkill):
    name = "file_manager"
    priority = 5  # High priority — very common user request

    def __init__(self, memory=None):
        super().__init__(memory)
        cfg = CONFIG.get("skills", {}).get("file_manager", {})
        default_dir = cfg.get("default_directory", "")
        if default_dir:
            self.default_dir = Path(default_dir)
        else:
            # Default to user's Desktop
            self.default_dir = Path.home() / "Desktop"
        self.default_dir.mkdir(parents=True, exist_ok=True)

    def can_handle(self, text: str) -> bool:
        """Legacy keyword check — used when intent router is offline."""
        triggers = [
            "create a file", "create file", "make a file", "make file",
            "create a to-do", "create a todo", "make a list", "create a list",
            "add to file", "add to the file", "append to",
            "delete file", "delete the file", "remove file",
            "read file", "read the file", "show file", "show the file",
            "open file", "open the file", "edit file",
        ]
        return self._contains_any(text, triggers)

    def execute(self, text: str) -> str:
        """Legacy execution from raw text — used when intent router is offline."""
        return f"File manager received: {text}. Please use action-based execution."

    def execute_action(self, action: str, params: dict) -> str:
        """
        Execute file operation from structured action dict.
        
        Actions: file_create, file_read, file_edit, file_delete, file_open,
                 folder_create, folder_open
        """
        handler = {
            "file_create": self._create_file,
            "file_read": self._read_file,
            "file_edit": self._edit_file,
            "file_delete": self._delete_file,
            "file_open": self._open_file,
            "folder_create": self._create_folder,
            "folder_open": self._open_folder,
        }.get(action)

        if handler:
            return handler(params)
        return f"Unknown file action: {action}"

    def _resolve_path(self, params: dict) -> Path:
        """Get the full file path from params."""
        filename = params.get("filename", "")
        directory = params.get("directory", "")

        # Check chain context for filename if not provided
        if not filename:
            ctx = params.get("_chain_context", {})
            filename = ctx.get("last_filename", "")

        if not filename:
            return None

        # Clean filename — ensure it has an extension
        if "." not in filename:
            filename += ".txt"

        # Determine directory
        if directory:
            base = Path(directory)
        else:
            base = self.default_dir

        return base / filename

    def _create_file(self, params: dict) -> str:
        """Create a new file with optional content."""
        filepath = self._resolve_path(params)
        if not filepath:
            return "I need a filename to create, Sir. Try saying 'create a file called todo'."

        content = params.get("content", "")

        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)

            if filepath.exists():
                return f"File '{filepath.name}' already exists at {filepath.parent}, Sir. Shall I overwrite it?"

            filepath.write_text(content if content else "", encoding="utf-8")
            
            msg = f"File '{filepath.name}' created"
            if content:
                lines = content.strip().split("\n")
                msg += f" with {len(lines)} line{'s' if len(lines) > 1 else ''}"
            msg += f" at {filepath.parent}, Sir."
            
            logger.info(f"FileManager: Created {filepath}")
            return msg

        except Exception as e:
            logger.error(f"FileManager create error: {e}")
            return f"I couldn't create the file, Sir: {e}"

    def _read_file(self, params: dict) -> str:
        """Read and return file contents."""
        filepath = self._resolve_path(params)
        if not filepath:
            return "Which file would you like me to read, Sir?"

        try:
            if not filepath.exists():
                # Try searching in default dir
                return f"I couldn't find '{filepath.name}', Sir. It doesn't exist at {filepath.parent}."

            content = filepath.read_text(encoding="utf-8").strip()
            if not content:
                return f"The file '{filepath.name}' is empty, Sir."

            lines = content.split("\n")
            if len(lines) > 20:
                preview = "\n".join(lines[:20])
                return f"Here's the content of '{filepath.name}' (showing first 20 of {len(lines)} lines), Sir:\n{preview}"
            
            return f"Here's the content of '{filepath.name}', Sir:\n{content}"

        except Exception as e:
            logger.error(f"FileManager read error: {e}")
            return f"I couldn't read the file, Sir: {e}"

    def _edit_file(self, params: dict) -> str:
        """Edit a file: add lines, remove lines, or replace content."""
        filepath = self._resolve_path(params)
        if not filepath:
            return "Which file would you like me to edit, Sir?"

        try:
            # Create file if it doesn't exist
            if not filepath.exists():
                filepath.write_text("", encoding="utf-8")

            content = filepath.read_text(encoding="utf-8")
            lines = content.split("\n") if content else []

            # Add lines
            add_lines = params.get("add_lines", [])
            if add_lines:
                if isinstance(add_lines, str):
                    add_lines = [add_lines]
                for line in add_lines:
                    lines.append(line)
                filepath.write_text("\n".join(lines), encoding="utf-8")
                logger.info(f"FileManager: Added {len(add_lines)} lines to {filepath}")
                return f"Added {len(add_lines)} item{'s' if len(add_lines) > 1 else ''} to '{filepath.name}', Sir."

            # Remove lines
            remove_lines = params.get("remove_lines", [])
            if remove_lines:
                if isinstance(remove_lines, str):
                    remove_lines = [remove_lines]
                original_count = len(lines)
                for remove_text in remove_lines:
                    lines = [l for l in lines if remove_text.lower() not in l.lower()]
                removed_count = original_count - len(lines)
                filepath.write_text("\n".join(lines), encoding="utf-8")
                logger.info(f"FileManager: Removed {removed_count} lines from {filepath}")
                return f"Removed {removed_count} item{'s' if removed_count != 1 else ''} from '{filepath.name}', Sir."

            # Full content replacement
            new_content = params.get("content", "")
            if new_content:
                filepath.write_text(new_content, encoding="utf-8")
                return f"Updated the content of '{filepath.name}', Sir."

            return "What changes would you like me to make to the file, Sir?"

        except Exception as e:
            logger.error(f"FileManager edit error: {e}")
            return f"I couldn't edit the file, Sir: {e}"

    def _delete_file(self, params: dict) -> str:
        """Delete a file."""
        filepath = self._resolve_path(params)
        if not filepath:
            return "Which file would you like me to delete, Sir?"

        try:
            if not filepath.exists():
                return f"File '{filepath.name}' doesn't exist, Sir."

            filepath.unlink()
            logger.info(f"FileManager: Deleted {filepath}")
            return f"File '{filepath.name}' has been deleted, Sir."

        except Exception as e:
            logger.error(f"FileManager delete error: {e}")
            return f"I couldn't delete the file, Sir: {e}"

    def _open_file(self, params: dict) -> str:
        """Open a file in the default application. Searches system-wide if not found locally."""
        filepath = self._resolve_path(params)
        if not filepath:
            # Try raw text to extract filename
            raw = params.get("_raw", "")
            if raw:
                return self._search_and_open(raw, is_folder=False)
            return "Which file would you like me to open, Sir?"

        try:
            if filepath.exists():
                os.startfile(str(filepath))
                logger.info(f"FileManager: Opened {filepath}")
                return f"Opening '{filepath.name}' now, Sir."

            # File not in default dir -- search the whole system
            return self._search_and_open(filepath.name, is_folder=False)

        except Exception as e:
            logger.error(f"FileManager open error: {e}")
            return f"I couldn't open the file, Sir: {e}"

    def _create_folder(self, params: dict) -> str:
        """Create a new folder."""
        folder_name = params.get("folder_name", params.get("filename", ""))
        if not folder_name:
            # Try to extract from raw text
            raw = params.get("_raw", "")
            for prefix in ["create a folder called ", "create folder called ",
                           "make a folder called ", "create a folder named ",
                           "make folder ", "new folder ", "create folder "]:
                if prefix in raw.lower():
                    folder_name = raw[raw.lower().index(prefix) + len(prefix):].strip()
                    break
        if not folder_name:
            return "I need a folder name, Sir."

        directory = params.get("directory", "")
        base = Path(directory) if directory else self.default_dir
        folder_path = base / folder_name

        try:
            if folder_path.exists():
                return f"Folder '{folder_name}' already exists at {base}, Sir."
            folder_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"FileManager: Created folder {folder_path}")
            return f"Folder '{folder_name}' created at {base}, Sir."
        except Exception as e:
            logger.error(f"FileManager folder create error: {e}")
            return f"I couldn't create the folder, Sir: {e}"

    def _open_folder(self, params: dict) -> str:
        """Open a folder in Windows Explorer. Searches system-wide if needed."""
        folder_name = params.get("folder_name", params.get("filename", ""))
        if not folder_name:
            # Try to extract from raw
            raw = params.get("_raw", "")
            for prefix in ["open folder ", "open my ", "open the ", "open "]:
                if prefix in raw.lower():
                    folder_name = raw[raw.lower().index(prefix) + len(prefix):].strip()
                    # Remove trailing "folder" if present
                    if folder_name.lower().endswith(" folder"):
                        folder_name = folder_name[:-7].strip()
                    break

        if not folder_name:
            try:
                os.startfile(str(self.default_dir))
                return "Opening your default folder, Sir."
            except Exception as e:
                return f"I couldn't open the folder, Sir: {e}"

        # Check common folder aliases
        home = Path.home()
        known_folders = {
            "desktop": home / "Desktop",
            "downloads": home / "Downloads",
            "documents": home / "Documents",
            "pictures": home / "Pictures",
            "music": home / "Music",
            "videos": home / "Videos",
            "my documents": home / "Documents",
            "my pictures": home / "Pictures",
            "my music": home / "Music",
            "my downloads": home / "Downloads",
        }

        folder_path = known_folders.get(folder_name.lower())
        if folder_path and folder_path.exists():
            try:
                os.startfile(str(folder_path))
                logger.info(f"FileManager: Opened folder {folder_path}")
                return f"Opening '{folder_name}' folder, Sir."
            except Exception as e:
                return f"I couldn't open the folder, Sir: {e}"

        # Try default dir subdirectory
        check = self.default_dir / folder_name
        if check.exists() and check.is_dir():
            os.startfile(str(check))
            return f"Opening '{folder_name}' folder, Sir."

        # System-wide search
        return self._search_and_open(folder_name, is_folder=True)

    def _search_and_open(self, name: str, is_folder: bool = False) -> str:
        """Deep search the system for a file or folder and open it, using a fast BFS walker."""
        # Clean the name
        name = name.strip().strip('"').strip("'")
        for prefix in ["open ", "find ", "show ", "the file ", "the folder ",
                        "file ", "folder ", "called ", "named "]:
            if name.lower().startswith(prefix):
                name = name[len(prefix):].strip()

        if not name:
            kind = "folder" if is_folder else "file"
            return f"I need the name of the {kind} to find, Sir."

        logger.info(f"FileManager: Fast searching system for {'folder' if is_folder else 'file'} '{name}'")

        home = Path.home()
        # Places to start searching from (prioritized)
        start_dirs = [
            home / "Desktop", home / "Downloads", home / "Documents",
            home / "Pictures", home / "Music", home / "Videos",
            # Include custom project/game folders at root of home if they exist
            home
        ]

        # Folders that take forever to search / are useless for user files
        skip_dirs = {
            "appdata", "local settings", "application data", "windows",
            "program files", "program files (x86)", "node_modules",
            ".git", ".vscode", "temp", "tmp", "__pycache__"
        }

        target_lower = name.lower()
        best_match = None

        # Custom high-performance walker
        import os
        for base in start_dirs:
            if not base.exists():
                continue
            
            # BFS queue
            queue = [base]
            while queue:
                current = queue.pop(0)
                try:
                    with os.scandir(current) as entries:
                        for entry in entries:
                            entry_name_lower = entry.name.lower()
                            
                            # Skip heavy/hidden directories
                            if entry.is_dir() and (entry_name_lower in skip_dirs or entry.name.startswith(".")):
                                continue
                                
                            # Check match
                            if (is_folder and entry.is_dir()) or (not is_folder and not entry.is_dir()):
                                if target_lower == entry_name_lower:
                                    best_match = Path(entry.path)
                                    break # Exact match found
                                elif target_lower in entry_name_lower and best_match is None:
                                    best_match = Path(entry.path) # Partial match found

                            # Add dir to queue
                            if entry.is_dir():
                                queue.append(Path(entry.path))
                except (PermissionError, FileNotFoundError):
                    continue
                
                if best_match and best_match.name.lower() == target_lower:
                    break # Stop overall search if exact match found
            
            if best_match and best_match.name.lower() == target_lower:
                break # Stop base loop

        if best_match and best_match.exists():
            try:
                os.startfile(str(best_match))
                kind = "folder" if is_folder else "file"
                logger.info(f"FileManager: Found and opened {best_match}")
                return f"Found it! Opening '{best_match.name}' right away, Sir."
            except Exception as e:
                return f"I found it at {best_match}, Sir, but I ran into a permission error opening it: {e}"

        kind = "folder" if is_folder else "file"
        return f"I deeply searched your system but couldn't find a {kind} named '{name}', Sir."
