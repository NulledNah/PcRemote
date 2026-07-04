import json
import struct
from typing import Optional


PROTOCOL_VERSION = 2

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
MSG_VOLUME_STATUS = "vs"
MSG_AUTH = "au"
MSG_PING = "pi"
MSG_PONG = "po"


def encode_text(data: str) -> bytes:
    return json.dumps(data).encode("utf-8")


def encode_binary_mouse_move(dx: float, dy: float) -> bytes:
    return struct.pack("!cii", b'm', int(dx), int(dy))


def encode_text_message(msg_type: str, **kwargs) -> str:
    msg = {"t": msg_type, "v": PROTOCOL_VERSION}
    msg.update(kwargs)
    return json.dumps(msg)


def encode_volume_status(volume: int, muted: bool, source: str = "") -> str:
    return json.dumps({
        "t": MSG_VOLUME_STATUS,
        "f": source,
        "v": volume,
        "m": muted,
        "v2": PROTOCOL_VERSION,
    })


def decode_message(raw: str) -> Optional[dict]:
    try:
        data = json.loads(raw)
        if not isinstance(data, dict) or "t" not in data:
            return None
        return data
    except (json.JSONDecodeError, TypeError):
        return None
