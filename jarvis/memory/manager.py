"""
JARVIS Memory System
- Short-term: in-memory conversation context (managed by Brain)
- Long-term: SQLite for structured facts + ChromaDB for semantic recall
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path

from jarvis.config import CONFIG, ROOT_DIR
from jarvis.logger import logger


class MemoryManager:
    """
    Manages JARVIS long-term memory.
    Stores facts user tells JARVIS and retrieves relevant ones
    using semantic search.
    """

    def __init__(self):
        mem_cfg = CONFIG.get("memory", {})
        self.enabled = mem_cfg.get("long_term_enabled", True)
        db_path = ROOT_DIR / mem_cfg.get("db_path", "data/memory/jarvis_memory.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = str(db_path)
        self._chroma_path = str(ROOT_DIR / mem_cfg.get("embeddings_path", "data/memory/chroma"))
        self._db = None
        self._collection = None
        self._embedder = None

        if self.enabled:
            self._init_sqlite()
            self._init_chroma()

    # ── SQLite (structured facts) ──────────────────────────
    def _init_sqlite(self):
        self._db = sqlite3.connect(self._db_path, check_same_thread=False)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                tags TEXT DEFAULT ''
            )
        """)
        self._db.commit()
        logger.info(f"Memory SQLite ready at {self._db_path}")

    def _init_chroma(self):
        try:
            import chromadb
            from chromadb.config import Settings
            client = chromadb.PersistentClient(path=self._chroma_path)
            self._collection = client.get_or_create_collection("jarvis_memories")
            logger.info("ChromaDB memory collection ready.")
        except ImportError:
            logger.warning("ChromaDB not installed — semantic memory disabled.")
            self._collection = None
        except Exception as e:
            logger.warning(f"ChromaDB init failed: {e}")
            self._collection = None

    # ── Store a memory ─────────────────────────────────────
    def remember(self, content: str, tags: str = "") -> int:
        """Save a fact to long-term memory."""
        if not self.enabled or not content.strip():
            return -1

        # SQLite
        cur = self._db.execute(
            "INSERT INTO memories (content, tags) VALUES (?, ?)",
            (content.strip(), tags)
        )
        mem_id = cur.lastrowid
        self._db.commit()

        # ChromaDB (for semantic search)
        if self._collection:
            try:
                self._collection.add(
                    documents=[content],
                    ids=[str(mem_id)],
                    metadatas=[{"tags": tags, "created_at": datetime.now().isoformat()}]
                )
            except Exception as e:
                logger.warning(f"ChromaDB add failed: {e}")

        logger.info(f"Memory stored (id={mem_id}): {content[:60]}")
        return mem_id

    # ── Recall relevant memories ───────────────────────────
    def recall(self, query: str, n_results: int = 3) -> str:
        """
        Find relevant long-term memories for a query.
        Returns formatted string to inject into LLM context.
        """
        if not self.enabled or not self._collection:
            return ""

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=min(n_results, self._collection.count() or 1),
            )
            docs = results.get("documents", [[]])[0]
            if not docs:
                return ""
            return "\n".join(f"- {d}" for d in docs)
        except Exception as e:
            logger.warning(f"Memory recall error: {e}")
            return ""

    # ── List all memories ──────────────────────────────────
    def list_all(self) -> list[dict]:
        if not self._db:
            return []
        rows = self._db.execute(
            "SELECT id, content, created_at, tags FROM memories ORDER BY id DESC"
        ).fetchall()
        return [{"id": r[0], "content": r[1], "created_at": r[2], "tags": r[3]} for r in rows]

    def forget(self, mem_id: int):
        """Delete a specific memory by id."""
        if self._db:
            self._db.execute("DELETE FROM memories WHERE id=?", (mem_id,))
            self._db.commit()
        if self._collection:
            try:
                self._collection.delete(ids=[str(mem_id)])
            except Exception:
                pass
        logger.info(f"Memory {mem_id} deleted.")
