import json
from typing import Optional


MSG_MOUSE_MOVE = "m"
MSG_MOUSE_DOWN = "md"
MSG_MOUSE_UP = "mu"
MSG_MOUSE_SCROLL = "s"
MSG_KEY_DOWN = "kd"
MSG_KEY_UP = "ku"
MSG_KEY_TAP = "kt"
MSG_TYPE_TEXT = "tx"
MSG_VOLUME_GET = "vg"
MSG_VOLUME_SET = "vs"
MSG_VOLUME_MUTE = "vm"
MSG_AUTH = "au"
MSG_PING = "pi"
MSG_PONG = "po"


def decode_message(raw: str) -> Optional[dict]:
    try:
        data = json.loads(raw)
        if not isinstance(data, dict) or "t" not in data:
            return None
        return data
    except (json.JSONDecodeError, TypeError):
        return None
