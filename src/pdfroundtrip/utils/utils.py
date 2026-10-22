import os
import sys
import subprocess
from logger import LoggerManager

_logger = LoggerManager.get_named_logger(__name__)


def open_file(path):
    if sys.platform == 'win32':
        os.startfile(path)  # Windows native
    elif sys.platform == 'darwin':
        subprocess.run(['open', path])  # macOS
    else:
        try:
            subprocess.run(['xdg-open', path])  # Linux / other Unix
        except FileNotFoundError:
            _logger.warning("No known file opener command found.")


def to_list(data: list | dict | None) -> list:
    if data is None:
        return []
    return list(data.values()) if isinstance(data, dict) else data

