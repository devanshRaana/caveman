"""
JARVIS — Centralized Logger
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from jarvis.config import ROOT_DIR, CONFIG

_setup_done = False


def setup_logger() -> logging.Logger:
    global _setup_done

    log_cfg = CONFIG.get("logging", {})
    level_str = log_cfg.get("level", "INFO")
    level = getattr(logging, level_str.upper(), logging.INFO)

    log_path = ROOT_DIR / log_cfg.get("log_file", "logs/jarvis.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("JARVIS")
    if _setup_done:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    )

    # Console handler (UTF-8 safe — main.py reconfigures stdout to utf-8)
    import sys as _sys
    ch = logging.StreamHandler(_sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File handler (rotating)
    fh = RotatingFileHandler(
        log_path,
        maxBytes=log_cfg.get("max_bytes", 5_242_880),
        backupCount=log_cfg.get("backup_count", 3),
    )
    fh.setLevel(level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    _setup_done = True
    return logger


logger = setup_logger()
