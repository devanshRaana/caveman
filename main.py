"""
JARVIS — Main Orchestrator V2.1
The central brain that wires together:
  Audio pipeline → Intent Router → Skills / Command Chain → LLM Brain → TTS response

Features:
  - LLM-powered intent classification (not just keywords)
  - Command chaining (c1 → c2 → c3)
  - File management, browser automation, web search
  - Seamless online/offline switching
  - 30-second sleep mode with wake word activation
  - Auto-boot on laptop startup

Run this file to start JARVIS.
"""
import sys
import os

# ── Fix Windows cp1252 encoding crash ──────────────────────
# Force UTF-8 output so Unicode characters don't crash the console
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import time
import threading
import signal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from jarvis.config import CONFIG
from jarvis.logger import logger
from jarvis.audio.microphone import MicrophoneStream
from jarvis.audio.stt import SpeechToText
from jarvis.audio.tts import TextToSpeech
from jarvis.audio.wake_word import WakeWordDetector
from jarvis.brain.llm import Brain
from jarvis.brain.intent_router import IntentRouter
from jarvis.brain.command_chain import CommandChain
from jarvis.memory.manager import MemoryManager
from jarvis.skills.registry import SkillRegistry

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    console = Console()
    RICH = True
except ImportError:
    RICH = False


# Sleep timeout in seconds
SLEEP_TIMEOUT = 30


class JARVIS:
    """
    The main JARVIS V2.1 assistant class.
    
    Modes:
      SLEEPING  — Listening ONLY for wake word. Mic is off. Low power.
      AWAKE     — Actively listening and processing commands.
      
    Flow:
      1. Boot → greet → AWAKE  
      2. Wait for speech (voice only — no typing)
      3. If no interaction for 30s → SLEEPING
      4. Wake word "Hey JARVIS" → AWAKE
      5. Process command → speak response → back to step 2
    """
    BOOT_LINES = [
        "J.A.R.V.I.S. V2 — Just A Rather Very Intelligent System",
        "All systems online. Running fully local. Privacy secured.",
        "Intent Router: Active. Command Chains: Ready.",
    ]

    GOODBYE_PHRASES = ["goodbye jarvis", "bye jarvis", "shut down jarvis",
                       "stop jarvis", "exit jarvis", "quit jarvis"]
    CLEAR_CHAT_PHRASES = ["clear chat", "reset conversation", "new conversation",
                          "clear history", "start over"]

    def __init__(self):
        self._running = False
        self._awake = threading.Event()
        self._listening_lock = threading.Lock()
        self._last_interaction = time.time()
        self._sleep_mode = False
        self._tts = None  # Stored reference for interrupt
        logger.info("Initializing JARVIS V2.2 components…")

    def _print_banner(self):
        if RICH:
            console.print(Panel.fit(
                "[bold cyan]J.A.R.V.I.S V2[/bold cyan]\n"
                "[dim]Just A Rather Very Intelligent System[/dim]\n"
                "[green]● All systems online — Fully Local — Zero Cloud[/green]\n"
                "[yellow]● Voice-Only | Wake Word: 'Hey JARVIS'[/yellow]\n"
                "[blue]● File Manager | Browser | Web Search: Loaded[/blue]\n"
                "[magenta]● Sleep Mode: 30s inactivity | Auto-Boot: Enabled[/magenta]",
                border_style="cyan"
            ))
        else:
            print("=" * 55)
            print("  J.A.R.V.I.S V2 — Local Assistant")
            print("  Voice-only. Say 'Hey JARVIS' to wake me.")
            print("  I sleep after 30s of silence.")
            print("=" * 55)

    def _on_wake_word(self):
        """Called by WakeWordDetector when wake word is heard."""
        # If JARVIS is speaking, INTERRUPT him
        if self._tts and self._tts.is_speaking:
            logger.info("Wake word during speech — interrupting JARVIS!")
            self._tts.interrupt()
            if RICH:
                console.print("\n[bold yellow]⚡ Interrupted! Listening…[/bold yellow]")
            else:
                print("\n[Interrupted! Listening…]")

        if self._sleep_mode:
            logger.info("Wake word detected — waking up from sleep!")
            self._sleep_mode = False
        self._last_interaction = time.time()
        if not self._listening_lock.locked():
            self._awake.set()

    def _speak_and_log(self, tts: TextToSpeech, text: str):
        if RICH:
            console.print(f"[bold cyan]JARVIS:[/bold cyan] {text}")
        else:
            print(f"\nJARVIS: {text}")
        tts.speak(text)
        self._last_interaction = time.time()

    def _sleep_watchdog(self, tts: TextToSpeech):
        """Background thread that puts JARVIS to sleep after 30s of no interaction."""
        while self._running:
            time.sleep(2)  # Check every 2 seconds
            if self._sleep_mode:
                continue  # Already sleeping

            elapsed = time.time() - self._last_interaction
            if elapsed >= SLEEP_TIMEOUT and not self._listening_lock.locked():
                self._sleep_mode = True
                self._awake.clear()
                logger.info(f"No interaction for {SLEEP_TIMEOUT}s — going to sleep.")
                if RICH:
                    console.print("\n[dim]💤 JARVIS is sleeping. Say 'Hey JARVIS' to wake me.[/dim]")
                else:
                    print("\n[JARVIS sleeping — say 'Hey JARVIS' to wake me]")
                # Gentle sleep notification (short so it doesn't feel intrusive)
                tts.speak("Going to sleep, Sir. Call me when you need me.")

    def run(self):
        """Main entry point — boots JARVIS and starts the voice loop."""
        self._print_banner()

        # Initialize all components
        logger.info("Loading V2.1 components…")
        tts = TextToSpeech()
        self._tts = tts  # Store reference for interrupt
        
        # Create speak helper for async skills and command chains
        def speak_fn(text):
            self._speak_and_log(tts, text)
            
        memory = MemoryManager()
        brain = Brain()
        skills = SkillRegistry(memory=memory, tts_callback=speak_fn)
        intent_router = IntentRouter()
        mic = MicrophoneStream()
        stt = SpeechToText()

        chain_engine = CommandChain(skills, tts=tts, speak_fn=speak_fn)

        # Always use wake word for JARVIS
        watcher = WakeWordDetector(on_detected_callback=self._on_wake_word)
        watcher.start()

        greeting = (
            "Good to be back, Sir. All systems nominal. "
            "I'm listening for your voice commands. "
            "Say 'Hey JARVIS' anytime you need me."
        )

        self._speak_and_log(tts, greeting)
        self._running = True
        self._awake.set()  # Start awake
        self._last_interaction = time.time()

        # Start sleep watchdog
        sleep_thread = threading.Thread(
            target=self._sleep_watchdog, args=(tts,), daemon=True
        )
        sleep_thread.start()

        # Handle Ctrl+C gracefully
        def _sig_handler(sig, frame):
            self.shutdown(tts, skills)
        signal.signal(signal.SIGINT, _sig_handler)
        signal.signal(signal.SIGTERM, _sig_handler)

        # ── Main Voice Loop ────────────────────────────────
        while self._running:
            # If sleeping, block until wake word triggers
            if self._sleep_mode:
                if RICH:
                    console.print("[dim]😴 Sleeping… waiting for wake word…[/dim]", end="\r")
                self._awake.wait()
                if not self._running:
                    break
                # Woken up!
                self._sleep_mode = False
                self._last_interaction = time.time()
                tts.speak("I'm here, Sir. What do you need?")
                if RICH:
                    console.print("\n[bold yellow]⚡ Awake! Listening…[/bold yellow]")
                else:
                    print("\n[JARVIS awake — listening]")
                continue

            # Wait for wake word if no recent interaction
            if not self._awake.is_set():
                self._awake.wait()
                if not self._running:
                    break
                if self._sleep_mode:
                    continue

                self._last_interaction = time.time()
                tts.speak("Yes, Sir?")
                if RICH:
                    console.print("[bold yellow]⚡ Listening…[/bold yellow]")
                else:
                    print("\n[Listening…]")

            with self._listening_lock:
                # Record voice utterance
                audio_path = mic.record_utterance()
                if not audio_path:
                    time.sleep(0.1)
                    continue

                # Transcribe speech to text
                user_text = stt.transcribe(audio_path)
                if not user_text or len(user_text.strip()) < 2:
                    continue

                self._last_interaction = time.time()

                if RICH:
                    console.print(f"[bold green]You:[/bold green] {user_text}")
                else:
                    print(f"\nYou: {user_text}")

                # Check for goodbye
                if any(phrase in user_text.lower() for phrase in self.GOODBYE_PHRASES):
                    self.shutdown(tts, skills)
                    break

                # Check for clear history
                if any(phrase in user_text.lower() for phrase in self.CLEAR_CHAT_PHRASES):
                    brain.clear_history()
                    self._speak_and_log(tts, "Conversation history cleared, Sir.")
                    continue

                # ── V2: Intent-Based Routing ──────────────
                self._process_with_intent(
                    user_text, intent_router, skills, chain_engine, brain, memory, tts
                )

    def _process_with_intent(self, user_text, intent_router, skills,
                              chain_engine, brain, memory, tts):
        """
        Process user input through the intent router pipeline:
        1. Parse intent → structured action
        2. If chain → execute via CommandChain
        3. If single action → execute via SkillRegistry
        4. If general_chat → let LLM respond conversationally
        """
        # Parse intent
        if RICH:
            console.print("[dim]🧠 Analyzing command…[/dim]")

        intent = intent_router.parse(user_text)
        action = intent.get("action", "general_chat")

        logger.info(f"Intent parsed: {action}")
        if RICH:
            console.print(f"[dim]-> Intent: {action}[/dim]")

        # ── Command Chain ──────────────────────────────────
        if action == "chain":
            steps = intent.get("steps", [])
            if steps:
                result = chain_engine.execute(steps)
                if RICH:
                    console.print(f"[bold cyan]JARVIS:[/bold cyan] {result}")
                return

        # ── Web Search (Real-Time Knowledge RAG) ───────────
        if action == "web_search":
            if RICH:
                console.print("[dim]🔍 Searching the web for real-time information…[/dim]")
            else:
                print("\n[Searching the web…]")
                
            search_data = skills.execute_action(intent)
            brain.inject_context("system", f"[JARVIS searched the web for current data]")
            
            # Formulate RAG prompt to let the LLM synthesize the answer naturally
            user_text = (
                f"The user asked: '{user_text}'.\n\n"
                f"Here is the real-time data I retrieved from the web:\n"
                f"---\n{search_data}\n---\n\n"
                f"Based ONLY on this data, answer the user's question naturally and concisely. "
                f"Speak like JARVIS. Do not read out raw lists, URLs, or say 'Here is what I found'. "
                f"Just answer the question directly."
            )
            action = "general_chat"  # Fall through to the LLM chat block below

        # ── Single Action (Skill) ──────────────────────────
        if action != "general_chat" and action != "chain":
            skill_response = skills.execute_action(intent)
            if skill_response:
                self._speak_and_log(tts, skill_response)
                brain.inject_context("system",
                    f"[JARVIS executed '{action}' and responded: {skill_response}]")
                return

        # ── General Chat (LLM) — JARVIS speaks like a human ──
        memories = memory.recall(user_text) if memory.enabled else ""
        response_chunks = []
        sentence_buffer = ""

        if RICH:
            console.print("[bold cyan]JARVIS:[/bold cyan] ", end="")

        for chunk in brain.think(user_text, memories=memories):
            # Check if interrupted mid-stream
            if tts.was_interrupted():
                logger.info("LLM response interrupted by user.")
                if RICH:
                    console.print("\n[dim](interrupted)[/dim]")
                return

            response_chunks.append(chunk)
            sentence_buffer += chunk
            if RICH:
                console.print(chunk, end="")

            # Speak in sentence-sized chunks for natural-sounding output
            if any(sentence_buffer.rstrip().endswith(p) for p in [".", "!", "?", "...", "\n"]):
                clean = sentence_buffer.strip()
                if clean:
                    tts.speak(clean)
                    # Check if interrupted while speaking
                    if tts.was_interrupted():
                        logger.info("Speech interrupted by user during sentence.")
                        if RICH:
                            console.print("\n[dim](interrupted)[/dim]")
                        return
                sentence_buffer = ""

        # Speak any remaining text
        if sentence_buffer.strip():
            tts.speak(sentence_buffer.strip())

        if RICH:
            console.print()

        self._last_interaction = time.time()

    def shutdown(self, tts: TextToSpeech = None, skills: SkillRegistry = None):
        self._running = False
        self._awake.set()  # Unblock if waiting
        if skills:
            skills.cleanup()
        if tts:
            tts.speak("Shutting down all systems. Goodbye, Sir.")
        logger.info("JARVIS V2.1 shutdown complete.")
        if RICH:
            console.print("\n[bold red]JARVIS offline.[/bold red]")
        sys.exit(0)


def main():
    jarvis = JARVIS()
    jarvis.run()


if __name__ == "__main__":
    main()
