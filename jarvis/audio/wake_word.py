"""
JARVIS Audio — Wake Word Detector
Uses OpenWakeWord for always-on "Hey JARVIS" detection.
Falls back to simple energy + keyword detection if needed.
"""
import threading
import time
import queue
import numpy as np
import sounddevice as sd

from jarvis.config import CONFIG
from jarvis.logger import logger


class WakeWordDetector:
    """
    Listens continuously in the background.
    Calls `on_detected()` callback when wake word is heard.
    """

    def __init__(self, on_detected_callback):
        ww_cfg = CONFIG.get("wake_word", {})
        audio_cfg = CONFIG.get("audio", {})
        self.enabled = ww_cfg.get("enabled", True)
        self.keyword = ww_cfg.get("keyword", "hey jarvis")
        self.sensitivity = ww_cfg.get("sensitivity", 0.6)
        self.engine = ww_cfg.get("engine", "openwakeword")
        self.sample_rate = audio_cfg.get("sample_rate", 16000)
        self.chunk = 1280  # OpenWakeWord needs exactly 1280 frames @ 16kHz
        self.device = audio_cfg.get("input_device_index", None)
        self.on_detected = on_detected_callback
        self._running = False
        self._thread = None
        self._model = None

    def _load_model(self):
        if self.engine == "openwakeword":
            try:
                from openwakeword.model import Model
                self._model = Model(
                    wakeword_models=["hey_jarvis"],
                    inference_framework="tflite",
                )
                logger.info("OpenWakeWord model loaded.")
                return True
            except Exception as e:
                logger.warning(f"OpenWakeWord load failed: {e}. Using energy fallback.")
                self.engine = "energy_fallback"
                return False
        return True

    # ── OpenWakeWord detection loop ────────────────────────
    def _run_openwakeword(self):
        q: queue.Queue = queue.Queue()

        def _cb(indata, frames, time_info, status):
            q.put(bytes(indata))

        logger.info("Wake word detector running. Say 'Hey JARVIS'…")
        with sd.RawInputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=self.chunk,
            device=self.device,
            callback=_cb,
        ):
            while self._running:
                data = q.get()
                np_data = np.frombuffer(data, dtype=np.int16)
                preds = self._model.predict(np_data)
                for wake_word, score in preds.items():
                    if score >= self.sensitivity:
                        logger.info(f"Wake word detected! (score={score:.2f})")
                        self.on_detected()
                        # Pause briefly so we don't double-trigger
                        time.sleep(1.5)

    # ── Energy fallback (keyword not checked, just energy spike) ──
    def _run_energy_fallback(self):
        """
        Simple always-listen fallback:
        Press Ctrl+` or shout to trigger (high-energy spike).
        Actually we'll use a simple threshold + short phrase detection.
        """
        import speech_recognition as sr
        r = sr.Recognizer()
        mic = sr.Microphone(sample_rate=self.sample_rate)
        logger.info("Using speech_recognition fallback for wake word…")
        with mic as source:
            r.adjust_for_ambient_noise(source, duration=1)

        while self._running:
            try:
                with mic as source:
                    audio = r.listen(source, timeout=5, phrase_time_limit=4)
                try:
                    text = r.recognize_google(audio).lower()  # uses local if available
                except Exception:
                    text = ""
                if self.keyword in text:
                    logger.info("Wake word detected via fallback.")
                    self.on_detected()
            except Exception:
                pass

    def start(self):
        if not self.enabled:
            logger.info("Wake word disabled — JARVIS will listen continuously.")
            return
        self._load_model()
        self._running = True
        target = self._run_openwakeword if self.engine == "openwakeword" else self._run_energy_fallback
        self._thread = threading.Thread(target=target, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
