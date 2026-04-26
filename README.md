# JARVIS — Local Personal Assistant

> **Just A Rather Very Intelligent System**
> 100% local. Zero cloud. Zero privacy risk.

---

## Features

| Feature | Details |
|---|---|
| Wake Word | "Hey JARVIS" — always listening |
| Voice Input | Whisper AI — best local STT available |
| AI Brain | Ollama + Mistral 7B — fully local LLM |
| Voice Output | pyttsx3 — natural local TTS |
| Long-term Memory | ChromaDB + SQLite — remembers what you tell it |
| Skills | Time, Apps, Notes, Files, System, Clipboard |
| System Tray | Boots silently, lives in your taskbar |
| Auto-startup | Boots with Windows via Task Scheduler |

---

## Quick Start

### Step 1 — Prerequisites
- Python 3.10+ → [python.org](https://python.org)
- Ollama → [ollama.ai/download](https://ollama.ai/download)

### Step 2 — Install
```bat
install.bat
```

### Step 3 — Pull an LLM
```bat
ollama pull mistral
```
> Note: **Your setup (32GB RAM) → use `llama3`** — it's the best:
> - 8 GB RAM → `ollama pull phi3`
> - 16 GB RAM → `ollama pull mistral`
> - **32 GB RAM → `ollama pull llama3` ← YOU ARE HERE**

### Step 4 — Run JARVIS
```bat
venv\Scripts\activate.bat
python main.py
```

### Step 5 — Auto-start on Boot (optional)
```bat
# Right-click and "Run as Administrator":
register_startup.bat
```

---

## What You Can Say

| Say... | JARVIS Does... |
|---|---|
| "Hey JARVIS" | Wakes up and listens |
| "What time is it?" | Tells you the time |
| "Open Chrome" | Launches Chrome |
| "Take a note — buy groceries" | Saves a note |
| "Read my notes" | Reads back your notes |
| "Remember my birthday is March 5th" | Stores in long-term memory |
| "What do you remember about my birthday?" | Recalls it |
| "What's my battery level?" | Reports battery % |
| "Mute the audio" | Mutes system sound |
| "Shutdown the computer" | Initiates shutdown |
| "Find file resume.pdf" | Searches your files |
| "Read my clipboard" | Reads clipboard content |
| "Clear history" | Resets conversation |
| "Goodbye JARVIS" | Shuts JARVIS down |
| *Anything else* | Answered by Mistral LLM |

---

## Project Structure

```
JARVIS/
├── main.py                   # Entry point — run this
├── jarvis_startup.pyw        # Silent startup (no console)
├── config.yaml               # All settings here
├── install.bat               # One-click installer
├── register_startup.bat      # Add to Windows startup
├── requirements.txt
├── jarvis/
│   ├── audio/
│   │   ├── microphone.py     # Mic capture + silence detection
│   │   ├── wake_word.py      # "Hey JARVIS" detection
│   │   ├── stt.py            # Whisper speech-to-text
│   │   └── tts.py            # Local text-to-speech
│   ├── brain/
│   │   └── llm.py            # Ollama LLM client + history
│   ├── memory/
│   │   └── manager.py        # Long-term memory (SQLite + ChromaDB)
│   ├── skills/
│   │   ├── registry.py       # Routes voice to skills
│   │   ├── datetime_skill.py
│   │   ├── memory_skill.py
│   │   ├── app_launcher.py
│   │   ├── notes_skill.py
│   │   ├── system_control.py
│   │   ├── file_search.py
│   │   └── clipboard_skill.py
│   ├── tray.py               # System tray icon
│   └── config.py / logger.py
└── data/
    ├── notes/notes.txt       # Your voice notes
    └── memory/               # JARVIS memory database
```

---

## Configuration

Edit `config.yaml` to customize everything:
- **LLM model** — switch between mistral, phi3, llama3
- **Wake word sensitivity** — tune false positive rate
- **Whisper model size** — tiny/base/small (speed vs accuracy)
- **Voice rate** — how fast JARVIS speaks
- **Always-listen mode** — disable wake word entirely

---

## Privacy

- All AI runs on your device
- No microphone data ever leaves your laptop
- No API keys, no internet required
- Memory stored in local SQLite database
- Works 100% offline
