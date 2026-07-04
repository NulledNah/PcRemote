import logging
import os
import sys
from datetime import datetime

from .config import get_data_dir


_logger = None


def setup(level: int = logging.INFO) -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger

    _logger = logging.getLogger("pcremote")
    _logger.setLevel(level)
    _logger.handlers.clear()

    console_fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
    )
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(console_fmt)
    _logger.addHandler(ch)

    try:
        log_dir = get_data_dir()
        log_file = os.path.join(log_dir, f"pcremote-{datetime.now():%Y%m%d}.log")
        file_fmt = logging.Formatter(
            "%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(file_fmt)
        _logger.addHandler(fh)
    except Exception:
        pass

    return _logger


def get() -> logging.Logger:
    global _logger
    if _logger is None:
        return setup()
    return _logger
