"""
JARVIS Audio — Microphone Input Handler
Captures audio from the default mic with silence detection.
"""
import threading
import time
import queue
import numpy as np
import sounddevice as sd
import soundfile as sf
import tempfile
import os

from jarvis.config import CONFIG
from jarvis.logger import logger


class MicrophoneStream:
    """
    Continuous ring-buffer microphone capture.
    Detects speech start/end via RMS energy threshold.
    """

    def __init__(self):
        audio_cfg = CONFIG.get("audio", {})
        stt_cfg = CONFIG.get("stt", {})
        self.sample_rate = audio_cfg.get("sample_rate", 16000)
        self.channels = audio_cfg.get("channels", 1)
        self.chunk = audio_cfg.get("chunk_size", 1024)
        self.device = audio_cfg.get("input_device_index", None)
        self.silence_dur = stt_cfg.get("silence_duration", 1.5)
        self.max_sec = stt_cfg.get("max_listen_seconds", 30)

        self._stream = None
        self._q: queue.Queue = queue.Queue()
        self._active = False

    # ── Internal callback ──────────────────────────────────
    def _callback(self, indata, frames, time_info, status):
        if status:
            logger.debug(f"Mic status: {status}")
        self._q.put(bytes(indata))

    # ── High-level: record one utterance ──────────────────
    def record_utterance(self) -> str | None:
        """
        Record until silence is detected.
        Returns path to a WAV temp file, or None on error.
        """
        frames = []
        silence_chunks = 0
        speech_detected = False
        silence_threshold_rms = 200  # tune per environment
        silence_needed = int(self.silence_dur * self.sample_rate / self.chunk)
        max_chunks = int(self.max_sec * self.sample_rate / self.chunk)

        logger.debug("Listening for speech…")
        with sd.RawInputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            blocksize=self.chunk,
            device=self.device,
            callback=self._callback,
        ):
            chunk_count = 0
            while chunk_count < max_chunks:
                data = self._q.get()
                np_data = np.frombuffer(data, dtype=np.int16)
                rms = int(np.sqrt(np.mean(np_data.astype(np.float32) ** 2)))

                if rms > silence_threshold_rms:
                    speech_detected = True
                    silence_chunks = 0
                    frames.append(data)
                elif speech_detected:
                    frames.append(data)
                    silence_chunks += 1
                    if silence_chunks >= silence_needed:
                        break

                chunk_count += 1

        if not speech_detected or not frames:
            logger.debug("No speech detected.")
            return None

        # Write to temp WAV
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        audio_np = np.frombuffer(b"".join(frames), dtype=np.int16)
        sf.write(tmp.name, audio_np, self.sample_rate)
        logger.debug(f"Captured utterance -> {tmp.name}")
        return tmp.name
