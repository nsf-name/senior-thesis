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
        log_path: Path
    ) -> logging.handlers.QueueListener:
    """Get a logger suitable for use in a manager context."""
    out_handler = logging.StreamHandler()
    out_handler.setFormatter(_formatter)
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(_formatter)
    return logging.handlers.QueueListener(
        queue, out_handler, file_handler, respect_handler_level=True
    )
    
