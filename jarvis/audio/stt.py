"""
JARVIS Audio — Speech-to-Text (Whisper via faster-whisper)
Transcribes a WAV file to text, 100% locally.
"""
import os

from jarvis.config import CONFIG
from jarvis.logger import logger


class SpeechToText:
    def __init__(self):
        stt_cfg = CONFIG.get("stt", {})
        self.engine = stt_cfg.get("engine", "faster-whisper")
        self.model_size = stt_cfg.get("model_size", "base")
        self.language = stt_cfg.get("language", "en")
        self.device = stt_cfg.get("device", "cpu")
        self._model = None

    def _load(self):
        if self._model is not None:
            return
        logger.info(f"Loading Whisper model '{self.model_size}' on {self.device}…")
        try:
            from faster_whisper import WhisperModel
            compute = "int8" if self.device == "cpu" else "float16"
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=compute,
            )
            logger.info("Whisper model ready.")
        except ImportError:
            logger.error("faster-whisper not installed. Run: pip install faster-whisper")
            raise

    def transcribe(self, audio_path: str) -> str:
        """
        Transcribe a WAV file and return the text string.
        """
        self._load()
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return ""

        try:
            segments, info = self._model.transcribe(
                audio_path,
                language=self.language,
                beam_size=5,
                vad_filter=True,   # Filter silence
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            logger.debug(f"STT result: '{text}'")

            # Cleanup temp file
            try:
                os.unlink(audio_path)
            except Exception:
                pass

            return text
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return ""
