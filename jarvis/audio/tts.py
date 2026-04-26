"""
JARVIS Audio — Text-to-Speech V2.1 (Interruptible + Human-like)
Converts JARVIS responses to natural-sounding speech.
Supports MID-SPEECH INTERRUPTION — say "JARVIS" while he's talking to stop him.
"""
import threading
import re
import time

from jarvis.config import CONFIG
from jarvis.logger import logger


class TextToSpeech:
    def __init__(self):
        tts_cfg = CONFIG.get("tts", {})
        self.engine_name = tts_cfg.get("engine", "pyttsx3")
        self.rate = tts_cfg.get("voice_rate", 170)
        self.voice_id = tts_cfg.get("voice_id", None)
        self.volume = tts_cfg.get("volume", 0.95)
        self._engine = None
        self._lock = threading.Lock()
        self._interrupted = threading.Event()  # Set this to stop speech
        self._speaking = threading.Event()     # True while actively speaking
        self._init_engine()

    def _init_engine(self):
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self.rate)
            self._engine.setProperty("volume", self.volume)

            voices = self._engine.getProperty("voices")
            chosen_voice = None

            if self.voice_id:
                self._engine.setProperty("voice", self.voice_id)
                chosen_voice = self.voice_id
            else:
                priority_names = ["david", "mark", "george", "james", "daniel"]
                for v in voices:
                    name = v.name.lower()
                    for pname in priority_names:
                        if pname in name:
                            chosen_voice = v.id
                            break
                    if chosen_voice:
                        break

                if not chosen_voice and voices:
                    for v in voices:
                        name = v.name.lower()
                        if "male" in name:
                            chosen_voice = v.id
                            break

                if not chosen_voice and voices:
                    chosen_voice = voices[0].id

                if chosen_voice:
                    self._engine.setProperty("voice", chosen_voice)

            current_voice = self._engine.getProperty("voice")
            voice_name = "Unknown"
            for v in voices:
                if v.id == current_voice:
                    voice_name = v.name
                    break

            logger.info(f"TTS initialized. Voice: {voice_name}, Rate: {self.rate}")

        except Exception as e:
            logger.error(f"TTS init failed: {e}")
            self._engine = None

    @property
    def is_speaking(self) -> bool:
        """Check if JARVIS is currently speaking."""
        return self._speaking.is_set()

    def interrupt(self):
        """
        Interrupt JARVIS mid-speech. Called when wake word is detected
        while JARVIS is talking.
        """
        if self._speaking.is_set():
            logger.info("TTS interrupted by user!")
            self._interrupted.set()
            try:
                if self._engine:
                    self._engine.stop()
            except Exception:
                pass

    def _clean_text(self, text: str) -> str:
        """Clean text for more natural speech output."""
        if not text:
            return text
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'`(.*?)`', r'\1', text)
        text = re.sub(r'#{1,6}\s*', '', text)
        text = re.sub(r'https?://\S+', 'a link', text)
        text = re.sub(r'\n+', '. ', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'^\s*[-*•]\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'(\d+)\.\s', r'\1, ', text)
        return text.strip()

    def speak(self, text: str):
        """
        Speak text synchronously. Can be interrupted by calling interrupt().
        """
        if not text or not text.strip():
            return
        if self._engine is None:
            logger.warning(f"TTS unavailable. JARVIS would say: {text}")
            return

        # Check if already interrupted before starting
        if self._interrupted.is_set():
            self._interrupted.clear()
            return

        clean = self._clean_text(text)
        if not clean:
            return

        logger.debug(f"Speaking: {clean[:80]}…")
        self._speaking.set()
        try:
            with self._lock:
                self._engine.say(clean)
                self._engine.runAndWait()
        except RuntimeError as e:
            if "run loop already started" in str(e).lower():
                try:
                    self._engine.stop()
                except Exception:
                    pass
                self._init_engine()
                if not self._interrupted.is_set():
                    try:
                        with self._lock:
                            self._engine.say(clean)
                            self._engine.runAndWait()
                    except Exception:
                        pass
            else:
                logger.warning(f"TTS runtime error: {e}")
        except Exception as e:
            logger.error(f"TTS speak error: {e}")
            self._init_engine()
        finally:
            self._speaking.clear()

        # If interrupted, clear the flag for next use
        if self._interrupted.is_set():
            self._interrupted.clear()
            logger.info("TTS: Speech was interrupted, cleared flag.")

    def was_interrupted(self) -> bool:
        """Check and clear the interrupted flag. Returns True if speech was interrupted."""
        if self._interrupted.is_set():
            self._interrupted.clear()
            return True
        return False

    def speak_async(self, text: str):
        """Non-blocking speak — fire and forget."""
        t = threading.Thread(target=self.speak, args=(text,), daemon=True)
        t.start()
        return t
