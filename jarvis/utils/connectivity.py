"""
JARVIS Utility — Connectivity Manager
Detects internet availability for seamless online/offline switching.
"""
import socket
from jarvis.logger import logger


_last_status = None


def is_online(timeout: float = 2.0) -> bool:
    """
    Quick check if internet is available by connecting to DNS.
    Caches result briefly to avoid excessive checks.
    """
    global _last_status
    try:
        sock = socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        sock.close()
        if _last_status is not True:
            logger.info("Connectivity: Internet is available")
            _last_status = True
        return True
    except (socket.timeout, OSError):
        if _last_status is not False:
            logger.info("Connectivity: No internet connection")
            _last_status = False
        return False


def require_online(func):
    """Decorator that checks internet before executing."""
    def wrapper(*args, **kwargs):
        if not is_online():
            return "I'm currently offline, Sir. I'll need an internet connection for that."
        return func(*args, **kwargs)
    return wrapper
