import json
import os
from typing import Any, Dict

STATE_DIR = os.path.expanduser("~/.zinkx_dev_assistant")
os.makedirs(STATE_DIR, exist_ok=True)

CMD_FILE = os.path.join(STATE_DIR, "command.json")
STATUS_FILE = os.path.join(STATE_DIR, "status.json")


def send_command(cmd: Dict[str, Any]):
    with open(CMD_FILE, "w", encoding="utf-8") as f:
        json.dump(cmd, f)


def read_command() -> Dict[str, Any] | None:
    if not os.path.exists(CMD_FILE):
        return None
    try:
        with open(CMD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def clear_command():
    if os.path.exists(CMD_FILE):
        os.remove(CMD_FILE)


def write_status(status: Dict[str, Any]):
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f)


def read_status() -> Dict[str, Any] | None:
    if not os.path.exists(STATUS_FILE):
        return None
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
