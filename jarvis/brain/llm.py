"""
JARVIS Brain — Ollama LLM Client
Handles all conversation with the local LLM (Mistral/LLaMA/Phi3).
"""
import json
from typing import Generator

from jarvis.config import CONFIG
from jarvis.logger import logger


class Brain:
    """
    Wraps Ollama to provide a conversational LLM backend.
    Maintains conversation history for multi-turn dialogue.
    """

    SYSTEM_PROMPT_TEMPLATE = """
{personality}

Current date and time: {datetime}
Long-term memories available: {memories}
""".strip()

    def __init__(self):
        llm_cfg = CONFIG.get("llm", {})
        jarvis_cfg = CONFIG.get("jarvis", {})
        self.model = llm_cfg.get("model", "mistral")
        self.base_url = llm_cfg.get("base_url", "http://localhost:11434")
        self.temperature = llm_cfg.get("temperature", 0.7)
        self.max_tokens = llm_cfg.get("max_tokens", 512)
        self.stream = llm_cfg.get("stream", True)
        self.personality = jarvis_cfg.get("personality", "You are JARVIS, a helpful AI.")
        self.user_name = jarvis_cfg.get("user_name", "Sir")
        self._history: list[dict] = []
        self._client = None
        self._load_client()

    def _load_client(self):
        try:
            import ollama
            self._client = ollama
            # Quick ping to check Ollama is running
            self._client.list()
            logger.info(f"Ollama connected. Model: {self.model}")
        except Exception as e:
            logger.error(f"Ollama connection failed: {e}")
            logger.error("Make sure Ollama is running: https://ollama.ai")
            self._client = None

    def _build_system_prompt(self, memories: str = "") -> str:
        from datetime import datetime
        now = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        return self.SYSTEM_PROMPT_TEMPLATE.format(
            personality=self.personality,
            datetime=now,
            memories=memories if memories else "None",
        )

    def think(self, user_input: str, memories: str = "") -> Generator[str, None, None]:
        """
        Stream a response from the LLM.
        Yields text chunks as they arrive.
        """
        if not self._client:
            yield "I'm sorry, Sir. My brain module is offline. Please ensure Ollama is running."
            return

        system_msg = {"role": "system", "content": self._build_system_prompt(memories)}
        self._history.append({"role": "user", "content": user_input})

        messages = [system_msg] + self._history[-20:]  # keep last 20 turns

        try:
            full_response = ""
            response = self._client.chat(
                model=self.model,
                messages=messages,
                stream=self.stream,
                options={
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
            )

            if self.stream:
                for chunk in response:
                    token = chunk["message"]["content"]
                    full_response += token
                    yield token
            else:
                full_response = response["message"]["content"]
                yield full_response

            # Save assistant reply to history
            self._history.append({"role": "assistant", "content": full_response})

        except Exception as e:
            logger.error(f"LLM think error: {e}")
            yield f"I encountered an error, Sir: {str(e)}"

    def think_full(self, user_input: str, memories: str = "") -> str:
        """
        Non-streaming: return complete response string.
        """
        return "".join(self.think(user_input, memories))

    def clear_history(self):
        self._history = []
        logger.info("Conversation history cleared.")

    def inject_context(self, role: str, content: str):
        """Manually inject a message into history (e.g., skill results)."""
        self._history.append({"role": role, "content": content})
