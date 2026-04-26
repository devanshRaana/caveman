"""
JARVIS Brain — LLM-Powered Intent Router
Replaces keyword-based routing with intelligent command classification.
The LLM parses user input into structured actions.
"""
import json
import re
from typing import Optional
from jarvis.config import CONFIG
from jarvis.logger import logger


class IntentRouter:
    """
    Uses the local LLM (Ollama) to classify user utterances into
    structured action dicts:
      {"action": "file_create", "params": {"filename": "todo.txt", "content": "..."}}
    
    Also detects command chains:
      {"action": "chain", "steps": [action1, action2, action3]}
    """

    INTENT_SYSTEM_PROMPT = """You are JARVIS's intent classifier. Your ONLY job is to parse the user's command into a JSON action.

RESPOND WITH ONLY VALID JSON. No explanations, no markdown, no extra text.

Available actions and their params:

1. file_create: {"action":"file_create","params":{"filename":"name.txt","content":"file contents","directory":"optional path"}}
2. file_read: {"action":"file_read","params":{"filename":"name.txt","directory":"optional"}}
3. file_edit: {"action":"file_edit","params":{"filename":"name.txt","add_lines":["line1","line2"],"remove_lines":["line to remove"],"directory":"optional"}}
4. file_delete: {"action":"file_delete","params":{"filename":"name.txt","directory":"optional"}}
5. file_open: {"action":"file_open","params":{"filename":"name.txt","directory":"optional"}}
6. open_app: {"action":"open_app","params":{"app_name":"chrome"}}
7. close_app: {"action":"close_app","params":{"app_name":"chrome"}}
8. web_search: {"action":"web_search","params":{"query":"search terms"}}
9. open_url: {"action":"open_url","params":{"url":"https://..."}}
10. send_email: {"action":"send_email","params":{"to":"email@example.com","subject":"subject","body":"email body"}}
11. send_whatsapp: {"action":"send_whatsapp","params":{"contact":"contact name","message":"message text"}}
12. start_meet: {"action":"start_meet","params":{"meeting_link":"optional link"}}
13. start_video_call: {"action":"start_video_call","params":{"platform":"whatsapp|meet","contact":"optional"}}
14. youtube_search: {"action":"youtube_search","params":{"query":"search terms"}}
15. folder_create: {"action":"folder_create","params":{"folder_name":"folder name","directory":"optional path"}}
16. folder_open: {"action":"folder_open","params":{"folder_name":"folder name or desktop|downloads|documents"}}
17. system_control: {"action":"system_control","params":{"command":"volume_up|volume_down|mute|shutdown|restart|sleep|lock|battery|system_info","value":"optional"}}
18. take_note: {"action":"take_note","params":{"content":"note text"}}
19. read_notes: {"action":"read_notes","params":{}}
20. remember: {"action":"remember","params":{"fact":"thing to remember"}}
21. recall: {"action":"recall","params":{"query":"what to recall"}}
22. datetime: {"action":"datetime","params":{"query":"time|date|day"}}
23. play_spotify: {"action":"play_spotify","params":{"song_name":"song or artist name"}}
24. set_timer: {"action":"set_timer","params":{"duration":"10 minutes","name":"optional"}}
25. set_reminder: {"action":"set_reminder","params":{"duration":"1 hour","task":"call mom"}}
26. stopwatch_start: {"action":"stopwatch_start","params":{}}
27. stopwatch_stop: {"action":"stopwatch_stop","params":{}}
28. calculate: {"action":"calculate","params":{"expression":"5 * 5"}}
29. general_chat: {"action":"general_chat","params":{"message":"the user message"}}
30. youtube_play: {"action":"youtube_play","params":{"video_number":2}}
31. scroll_down: {"action":"scroll_down","params":{}}
32. scroll_up: {"action":"scroll_up","params":{}}
33. execute_code: {"action":"execute_code","params":{"prompt":"The user's instruction for offline automation or code to run"}}

For MULTIPLE commands (chains), respond with:
{"action":"chain","steps":[action1, action2, action3]}

RULES:
- If the user says "create a to-do list" → file_create with filename "todo.txt"
- If adding items to an existing file → file_edit with add_lines
- If the user asks about recent news, current events, real-time info, or facts you don't know → web_search
- If the user explicitly says "search for X" or "google X" → web_search
- If the user wants to search YouTube → youtube_search
- If the user wants to create a folder → folder_create
- If the user wants to open a folder (downloads, desktop etc) → folder_open
- If the user wants casual conversation, jokes, or personal questions → general_chat
- If unsure of the action, default to general_chat
- Parse "and then", "after that", "also" as chain commands
- For file operations, if no directory specified, leave directory empty
- If the user wants to play a specific video from YouTube search results, like "play the second video" → youtube_play with the video_number
- If the user says "scroll down" or "scroll up" → scroll_down or scroll_up
- If the user asks for offline automation, sending whatsapp autonomously, writing a python script, or complex tasks (Open Claw) → execute_code
- ALWAYS respond with valid JSON only"""

    def __init__(self):
        self._client = None
        llm_cfg = CONFIG.get("llm", {})
        self.model = llm_cfg.get("model", "mistral")
        self.base_url = llm_cfg.get("base_url", "http://localhost:11434")
        self._load_client()

    def _load_client(self):
        try:
            import ollama
            self._client = ollama
            logger.info("IntentRouter: Ollama connected for intent parsing")
        except Exception as e:
            logger.error(f"IntentRouter: Ollama connection failed: {e}")
            self._client = None

    def parse(self, user_text: str) -> dict:
        """
        Parse user text into a structured action dict.
        Falls back to keyword-based parsing if LLM fails.
        """
        if not self._client:
            return self._fallback_parse(user_text)

        try:
            response = self._client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.INTENT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_text},
                ],
                stream=False,
                options={
                    "temperature": 0.1,  # Low temp for deterministic parsing
                    "num_predict": 512,
                },
            )

            raw = response["message"]["content"].strip()
            logger.debug(f"IntentRouter raw LLM output: {raw}")

            # Extract JSON from response (handle markdown code blocks)
            json_str = self._extract_json(raw)
            result = json.loads(json_str)

            # Validate structure
            if "action" not in result:
                logger.warning("IntentRouter: No 'action' in LLM response, falling back")
                return self._fallback_parse(user_text)

            logger.info(f"IntentRouter parsed: action={result['action']}")
            return result

        except json.JSONDecodeError as e:
            logger.warning(f"IntentRouter: JSON parse failed ({e}), using fallback")
            return self._fallback_parse(user_text)
        except Exception as e:
            logger.error(f"IntentRouter error: {e}")
            return self._fallback_parse(user_text)

    def _extract_json(self, text: str) -> str:
        """Extract JSON from LLM response, handling markdown code blocks."""
        # Try to find JSON in code blocks
        code_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if code_block:
            return code_block.group(1).strip()

        # Try to find raw JSON object
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            return brace_match.group(0)

        return text

    def _fallback_parse(self, text: str) -> dict:
        """
        Keyword-based fallback when LLM is unavailable.
        Maintains backward compatibility with existing skill triggers.
        """
        t = text.lower().strip()

        # File operations
        if any(kw in t for kw in ["create a file", "create file", "make a file",
                                   "create a to-do", "create a todo", "make a list",
                                   "create a list", "make a to-do"]):
            # Extract filename hint
            return {"action": "file_create", "params": {"filename": "", "content": "", "_raw": text}}

        if any(kw in t for kw in ["add to", "append to", "write to", "put in"]):
            return {"action": "file_edit", "params": {"add_lines": [], "_raw": text}}

        if any(kw in t for kw in ["delete file", "remove file", "delete the file"]):
            return {"action": "file_delete", "params": {"_raw": text}}

        if any(kw in t for kw in ["read file", "read the file", "show file", "open file"]):
            return {"action": "file_read", "params": {"_raw": text}}

        # Folder operations (check BEFORE generic open)
        if any(kw in t for kw in ["create a folder", "create folder", "make a folder",
                                   "new folder", "make folder"]):
            return {"action": "folder_create", "params": {"_raw": text}}

        if any(kw in t for kw in ["open folder", "open my folder", "open downloads",
                                   "open desktop", "open documents", "open the folder",
                                   "show folder", "show downloads"]):
            return {"action": "folder_open", "params": {"_raw": text}}

        # Notes (check BEFORE generic open/read)
        if any(kw in t for kw in ["take a note", "note this", "write this down",
                                   "jot down", "save a note"]):
            return {"action": "take_note", "params": {"_raw": text}}

        if any(kw in t for kw in ["read my notes", "show my notes", "read notes"]):
            return {"action": "read_notes", "params": {}}

        # Email / WhatsApp / Meet (check BEFORE generic open/start)
        if any(kw in t for kw in ["send email", "send an email", "email to", "mail to",
                                   "send mail", "compose email"]):
            return {"action": "send_email", "params": {"_raw": text}}

        if any(kw in t for kw in ["send whatsapp", "whatsapp message", "message on whatsapp",
                                   "send a whatsapp"]):
            return {"action": "send_whatsapp", "params": {"_raw": text}}

        if any(kw in t for kw in ["start a meet", "google meet", "video call on meet",
                                   "join meeting", "start meeting"]):
            return {"action": "start_meet", "params": {"_raw": text}}

        if any(kw in t for kw in ["video call", "call on whatsapp"]):
            return {"action": "start_video_call", "params": {"_raw": text}}

        # YouTube (check BEFORE generic search)
        if any(kw in t for kw in ["youtube", "search youtube", "play on youtube",
                                   "search on youtube", "find on youtube"]):
            return {"action": "youtube_search", "params": {"query": text, "_raw": text}}

        # Spotify (check BEFORE generic open)
        if any(kw in t for kw in ["play on spotify", "play spotify", "spotify play",
                                   "play song", "play music"]):
            return {"action": "play_spotify", "params": {"song_name": text, "_raw": text}}

        # App control (AFTER meet/whatsapp/email/folder/spotify to avoid false matches)
        if any(kw in t for kw in ["open ", "launch ", "start "]):
            return {"action": "open_app", "params": {"_raw": text}}

        if any(kw in t for kw in ["close ", "quit ", "kill "]):
            return {"action": "close_app", "params": {"_raw": text}}

        # Web search
        if any(kw in t for kw in ["search", "google", "look up", "find online"]):
            return {"action": "web_search", "params": {"query": text, "_raw": text}}

        # System
        if any(kw in t for kw in ["volume", "mute", "brightness", "battery", "shutdown",
                                   "restart", "sleep", "lock", "system info"]):
            return {"action": "system_control", "params": {"_raw": text}}

        # Time
        if any(kw in t for kw in ["what time", "what's the time", "what date",
                                   "what day", "today's date"]):
            return {"action": "datetime", "params": {"_raw": text}}

        # Tools & Timers (BEFORE general chat)
        if any(kw in t for kw in ["set a timer", "timer for", "start a timer"]):
            return {"action": "set_timer", "params": {"duration": text, "_raw": text}}
            
        if any(kw in t for kw in ["remind me", "set a reminder", "reminder to"]):
            return {"action": "set_reminder", "params": {"duration": text, "task": text, "_raw": text}}
            
        if any(kw in t for kw in ["start stopwatch", "start a stopwatch", "start the stopwatch"]):
            return {"action": "stopwatch_start", "params": {"_raw": text}}
            
        if any(kw in t for kw in ["stop stopwatch", "stop the stopwatch"]):
            return {"action": "stopwatch_stop", "params": {"_raw": text}}
            
        if any(kw in t for kw in ["calculate", "what is", "math ", "times", "divided by", "plus", "minus"]):
            # Very basic check
            tokens = ["+", "-", "*", "/", "times", "divided", "plus", "minus", "percent"]
            if any(tok in t for tok in tokens) and any(str(d) in t for d in range(10)):
                return {"action": "calculate", "params": {"expression": text, "_raw": text}}

        # Browser scrolling
        if any(kw in t for kw in ["scroll down", "go down"]):
            return {"action": "scroll_down", "params": {"_raw": text}}
            
        if any(kw in t for kw in ["scroll up", "go up"]):
            return {"action": "scroll_up", "params": {"_raw": text}}

        # YouTube play by number
        if "play" in t and any(kw in t for kw in ["first", "second", "third", "fourth", "fifth", "number", " 1", " 2", " 3", " 4", " 5"]):
            num = 1
            if "second" in t or "number 2" in t or "number two" in t or " 2" in t:
                num = 2
            elif "third" in t or "number 3" in t or "number three" in t or " 3" in t:
                num = 3
            elif "fourth" in t or "number 4" in t or "number four" in t or " 4" in t:
                num = 4
            elif "fifth" in t or "number 5" in t or "number five" in t or " 5" in t:
                num = 5
            
            return {"action": "youtube_play", "params": {"video_number": num, "_raw": text}}

        if any(kw in t for kw in ["run code", "write a script", "execute python", "open claw", "openclaw", "offline automation", "python"]):
            return {"action": "execute_code", "params": {"prompt": text, "_raw": text}}

        # Default to general chat
        return {"action": "general_chat", "params": {"message": text}}
