from enum import IntEnum
import logging
import logging.handlers
import multiprocessing
from pathlib import Path

# baffled this isn't a part of Python already
class LogLevel(IntEnum):
    """Logging levels for type safety reasons."""
    DEBUG = logging.DEBUG        # 10
    INFO = logging.INFO          # 20
    WARNING = logging.WARNING    # 30
    ERROR = logging.ERROR        # 40
    CRITICAL = logging.CRITICAL  # 50

_formatter = logging.Formatter(
    fmt="[ %(levelname)s ] {%(name)s} (%(filename)s:%(lineno)d)\n%(message)s "
)

def conf_interactive_logger(
        name: str,
        level: LogLevel = LogLevel.WARNING
    ) -> logging.Logger:
    """Get a logger suitable for use in an interactive context."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        logger.addHandler(handler)
        handler.setFormatter(_formatter)
    return logger

def conf_worker_logger(
        name: str,
        queue: multiprocessing.Queue,
        level: LogLevel = LogLevel.WARNING
    ) -> logging.Logger:
    """Get a logger suitable for use in a worker context."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.handlers.QueueHandler(queue)
        logger.addHandler(handler)
        handler.setFormatter(_formatter)
    return logger

def conf_manager_logger(
        queue: multiprocessing.Queue,
        log_path: Path,
        to_console: bool = False
    ) -> logging.handlers.QueueListener:
    """Get a logger suitable for use in a manager context."""
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(_formatter)
    handlers = [file_handler]
    if to_console:
        out_handler = logging.StreamHandler()
        out_handler.setFormatter(_formatter)
        handlers.append(out_handler)
    return logging.handlers.QueueListener(
        queue, *handlers, respect_handler_level=True
    )
    
