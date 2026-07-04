#!/usr/bin/env python3
"""PC Remote companion server for Linux (Fedora).

Receives commands via WebSocket and simulates keyboard/mouse input via uinput.
Run: python3 server.py [--port PORT]
"""

import asyncio
import json
import argparse
import socket
import signal
import sys
import subprocess
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import websockets
from websockets.asyncio.server import serve

from evdev import UInput, ecodes, AbsInfo

PROTOCOL_VERSION = 1

CHAR_TO_KEY = {
    'a': ecodes.KEY_A, 'b': ecodes.KEY_B, 'c': ecodes.KEY_C,
    'd': ecodes.KEY_D, 'e': ecodes.KEY_E, 'f': ecodes.KEY_F,
    'g': ecodes.KEY_G, 'h': ecodes.KEY_H, 'i': ecodes.KEY_I,
    'j': ecodes.KEY_J, 'k': ecodes.KEY_K, 'l': ecodes.KEY_L,
    'm': ecodes.KEY_M, 'n': ecodes.KEY_N, 'o': ecodes.KEY_O,
    'p': ecodes.KEY_P, 'q': ecodes.KEY_Q, 'r': ecodes.KEY_R,
    's': ecodes.KEY_S, 't': ecodes.KEY_T, 'u': ecodes.KEY_U,
    'v': ecodes.KEY_V, 'w': ecodes.KEY_W, 'x': ecodes.KEY_X,
    'y': ecodes.KEY_Y, 'z': ecodes.KEY_Z,
}

SHIFT_MAP = {
    'A': 'a', 'B': 'b', 'C': 'c', 'D': 'd', 'E': 'e', 'F': 'f',
    'G': 'g', 'H': 'h', 'I': 'i', 'J': 'j', 'K': 'k', 'L': 'l',
    'M': 'm', 'N': 'n', 'O': 'o', 'P': 'p', 'Q': 'q', 'R': 'r',
    'S': 's', 'T': 't', 'U': 'u', 'V': 'v', 'W': 'w', 'X': 'x',
    'Y': 'y', 'Z': 'z',
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6',
    '&': '7', '*': '8', '(': '9', ')': '0', '_': '-', '+': '=',
    '{': '[', '}': ']', '|': '\\', ':': ';', '"': "'", '<': ',',
    '>': '.', '?': '/', '~': '`',
}

SYMBOL_MAP = {
    ' ': ecodes.KEY_SPACE,
    '-': ecodes.KEY_MINUS, '=': ecodes.KEY_EQUAL,
    '[': ecodes.KEY_LEFTBRACE, ']': ecodes.KEY_RIGHTBRACE,
    '\\': ecodes.KEY_BACKSLASH, ';': ecodes.KEY_SEMICOLON,
    "'": ecodes.KEY_APOSTROPHE, ',': ecodes.KEY_COMMA,
    '.': ecodes.KEY_DOT, '/': ecodes.KEY_SLASH, '`': ecodes.KEY_GRAVE,
    '\n': ecodes.KEY_ENTER, '\t': ecodes.KEY_TAB,
}

NAMED_KEYS = {
    'KEY_A': ecodes.KEY_A, 'KEY_B': ecodes.KEY_B, 'KEY_C': ecodes.KEY_C,
    'KEY_D': ecodes.KEY_D, 'KEY_E': ecodes.KEY_E, 'KEY_F': ecodes.KEY_F,
    'KEY_G': ecodes.KEY_G, 'KEY_H': ecodes.KEY_H, 'KEY_I': ecodes.KEY_I,
    'KEY_J': ecodes.KEY_J, 'KEY_K': ecodes.KEY_K, 'KEY_L': ecodes.KEY_L,
    'KEY_M': ecodes.KEY_M, 'KEY_N': ecodes.KEY_N, 'KEY_O': ecodes.KEY_O,
    'KEY_P': ecodes.KEY_P, 'KEY_Q': ecodes.KEY_Q, 'KEY_R': ecodes.KEY_R,
    'KEY_S': ecodes.KEY_S, 'KEY_T': ecodes.KEY_T, 'KEY_U': ecodes.KEY_U,
    'KEY_V': ecodes.KEY_V, 'KEY_W': ecodes.KEY_W, 'KEY_X': ecodes.KEY_X,
    'KEY_Y': ecodes.KEY_Y, 'KEY_Z': ecodes.KEY_Z,
    'KEY_0': ecodes.KEY_0, 'KEY_1': ecodes.KEY_1, 'KEY_2': ecodes.KEY_2,
    'KEY_3': ecodes.KEY_3, 'KEY_4': ecodes.KEY_4, 'KEY_5': ecodes.KEY_5,
    'KEY_6': ecodes.KEY_6, 'KEY_7': ecodes.KEY_7, 'KEY_8': ecodes.KEY_8,
    'KEY_9': ecodes.KEY_9,
    'KEY_MINUS': ecodes.KEY_MINUS, 'KEY_EQUAL': ecodes.KEY_EQUAL,
    'KEY_LEFTBRACE': ecodes.KEY_LEFTBRACE, 'KEY_RIGHTBRACE': ecodes.KEY_RIGHTBRACE,
    'KEY_BACKSLASH': ecodes.KEY_BACKSLASH, 'KEY_SEMICOLON': ecodes.KEY_SEMICOLON,
    'KEY_APOSTROPHE': ecodes.KEY_APOSTROPHE, 'KEY_COMMA': ecodes.KEY_COMMA,
    'KEY_DOT': ecodes.KEY_DOT, 'KEY_SLASH': ecodes.KEY_SLASH,
    'KEY_GRAVE': ecodes.KEY_GRAVE,
    'KEY_LEFTCTRL': ecodes.KEY_LEFTCTRL,
    'KEY_RIGHTCTRL': ecodes.KEY_RIGHTCTRL,
    'KEY_LEFTALT': ecodes.KEY_LEFTALT,
    'KEY_RIGHTALT': ecodes.KEY_RIGHTALT,
    'KEY_LEFTMETA': ecodes.KEY_LEFTMETA,
    'KEY_RIGHTMETA': ecodes.KEY_RIGHTMETA,
    'KEY_LEFTSHIFT': ecodes.KEY_LEFTSHIFT,
    'KEY_RIGHTSHIFT': ecodes.KEY_RIGHTSHIFT,
    'KEY_UP': ecodes.KEY_UP,
    'KEY_DOWN': ecodes.KEY_DOWN,
    'KEY_LEFT': ecodes.KEY_LEFT,
    'KEY_RIGHT': ecodes.KEY_RIGHT,
    'KEY_TAB': ecodes.KEY_TAB,
    'KEY_ESC': ecodes.KEY_ESC,
    'KEY_ENTER': ecodes.KEY_ENTER,
    'KEY_BACKSPACE': ecodes.KEY_BACKSPACE,
    'KEY_DELETE': ecodes.KEY_DELETE,
    'KEY_SPACE': ecodes.KEY_SPACE,
    'KEY_HOME': ecodes.KEY_HOME,
    'KEY_END': ecodes.KEY_END,
    'KEY_PAGEUP': ecodes.KEY_PAGEUP,
    'KEY_PAGEDOWN': ecodes.KEY_PAGEDOWN,
    'KEY_INSERT': ecodes.KEY_INSERT,
    'KEY_CAPSLOCK': ecodes.KEY_CAPSLOCK,
    'KEY_NUMLOCK': ecodes.KEY_NUMLOCK,
    'KEY_SCROLLLOCK': ecodes.KEY_SCROLLLOCK,
    'KEY_F1': ecodes.KEY_F1, 'KEY_F2': ecodes.KEY_F2,
    'KEY_F3': ecodes.KEY_F3, 'KEY_F4': ecodes.KEY_F4,
    'KEY_F5': ecodes.KEY_F5, 'KEY_F6': ecodes.KEY_F6,
    'KEY_F7': ecodes.KEY_F7, 'KEY_F8': ecodes.KEY_F8,
    'KEY_F9': ecodes.KEY_F9, 'KEY_F10': ecodes.KEY_F10,
    'KEY_F11': ecodes.KEY_F11, 'KEY_F12': ecodes.KEY_F12,
    'KEY_PRINT': ecodes.KEY_SYSRQ,
    'KEY_PAUSE': ecodes.KEY_PAUSE,
}

ITALIAN_CHAR_MAP = {
    'a': (ecodes.KEY_A, False),       'A': (ecodes.KEY_A, True),
    'b': (ecodes.KEY_B, False),       'B': (ecodes.KEY_B, True),
    'c': (ecodes.KEY_C, False),       'C': (ecodes.KEY_C, True),
    'd': (ecodes.KEY_D, False),       'D': (ecodes.KEY_D, True),
    'e': (ecodes.KEY_E, False),       'E': (ecodes.KEY_E, True),
    'f': (ecodes.KEY_F, False),       'F': (ecodes.KEY_F, True),
    'g': (ecodes.KEY_G, False),       'G': (ecodes.KEY_G, True),
    'h': (ecodes.KEY_H, False),       'H': (ecodes.KEY_H, True),
    'i': (ecodes.KEY_I, False),       'I': (ecodes.KEY_I, True),
    'j': (ecodes.KEY_J, False),       'J': (ecodes.KEY_J, True),
    'k': (ecodes.KEY_K, False),       'K': (ecodes.KEY_K, True),
    'l': (ecodes.KEY_L, False),       'L': (ecodes.KEY_L, True),
    'm': (ecodes.KEY_M, False),       'M': (ecodes.KEY_M, True),
    'n': (ecodes.KEY_N, False),       'N': (ecodes.KEY_N, True),
    'o': (ecodes.KEY_O, False),       'O': (ecodes.KEY_O, True),
    'p': (ecodes.KEY_P, False),       'P': (ecodes.KEY_P, True),
    'q': (ecodes.KEY_Q, False),       'Q': (ecodes.KEY_Q, True),
    'r': (ecodes.KEY_R, False),       'R': (ecodes.KEY_R, True),
    's': (ecodes.KEY_S, False),       'S': (ecodes.KEY_S, True),
    't': (ecodes.KEY_T, False),       'T': (ecodes.KEY_T, True),
    'u': (ecodes.KEY_U, False),       'U': (ecodes.KEY_U, True),
    'v': (ecodes.KEY_V, False),       'V': (ecodes.KEY_V, True),
    'w': (ecodes.KEY_W, False),       'W': (ecodes.KEY_W, True),
    'x': (ecodes.KEY_X, False),       'X': (ecodes.KEY_X, True),
    'y': (ecodes.KEY_Y, False),       'Y': (ecodes.KEY_Y, True),
    'z': (ecodes.KEY_Z, False),       'Z': (ecodes.KEY_Z, True),
    '0': (ecodes.KEY_0, False),       '1': (ecodes.KEY_1, False),
    '2': (ecodes.KEY_2, False),       '3': (ecodes.KEY_3, False),
    '4': (ecodes.KEY_4, False),       '5': (ecodes.KEY_5, False),
    '6': (ecodes.KEY_6, False),       '7': (ecodes.KEY_7, False),
    '8': (ecodes.KEY_8, False),       '9': (ecodes.KEY_9, False),
    ' ': (ecodes.KEY_SPACE, False),
    ',': (ecodes.KEY_COMMA, False),   '.': (ecodes.KEY_DOT, False),
    '-': (ecodes.KEY_SLASH, False),   '_': (ecodes.KEY_SLASH, True),
    "'": (ecodes.KEY_MINUS, False),   '?': (ecodes.KEY_MINUS, True),
    'ì': (ecodes.KEY_EQUAL, False),   '^': (ecodes.KEY_EQUAL, True),
    'è': (ecodes.KEY_LEFTBRACE, False), 'é': (ecodes.KEY_LEFTBRACE, True),
    '+': (ecodes.KEY_RIGHTBRACE, False), '*': (ecodes.KEY_RIGHTBRACE, True),
    'ò': (ecodes.KEY_SEMICOLON, False), 'ç': (ecodes.KEY_SEMICOLON, True),
    'à': (ecodes.KEY_APOSTROPHE, False),
    'ù': (ecodes.KEY_BACKSLASH, False),
    ';': (ecodes.KEY_COMMA, True),    ':': (ecodes.KEY_DOT, True),
    '!': (ecodes.KEY_1, True),        '"': (ecodes.KEY_2, True),
    '£': (ecodes.KEY_3, True),        '$': (ecodes.KEY_4, True),
    '%': (ecodes.KEY_5, True),        '&': (ecodes.KEY_6, True),
    '/': (ecodes.KEY_7, True),        '(': (ecodes.KEY_8, True),
    ')': (ecodes.KEY_9, True),        '=': (ecodes.KEY_0, True),
    '<': (ecodes.KEY_102ND, False),   '>': (ecodes.KEY_102ND, True),
    '\\': (ecodes.KEY_GRAVE, False),  '|': (ecodes.KEY_GRAVE, True),
    '§': (ecodes.KEY_BACKSLASH, True),
    '\n': (ecodes.KEY_ENTER, False),
    '\t': (ecodes.KEY_TAB, False),
    '\b': (ecodes.KEY_BACKSPACE, False),
    '€': (ecodes.KEY_E, False, True),
    '@': (ecodes.KEY_SEMICOLON, False, True),
    '#': (ecodes.KEY_APOSTROPHE, False, True),
    '~': (ecodes.KEY_EQUAL, False, True),
    '[': (ecodes.KEY_LEFTBRACE, False, True),
    ']': (ecodes.KEY_RIGHTBRACE, False, True),
    '{': (ecodes.KEY_LEFTBRACE, True, True),
    '}': (ecodes.KEY_RIGHTBRACE, True, True),
    '`': (ecodes.KEY_MINUS, False, True),
    '°': (ecodes.KEY_APOSTROPHE, True),
    'µ': (ecodes.KEY_M, False, True),
    'ñ': (ecodes.KEY_N, False, True), 'Ñ': (ecodes.KEY_N, True, True),
    '×': (ecodes.KEY_COMMA, True, True),
    '÷': (ecodes.KEY_SLASH, True, True),
    '¥': (ecodes.KEY_Y, True, True),
    '«': (ecodes.KEY_Z, False, True),
    '»': (ecodes.KEY_X, False, True),
    '·': (ecodes.KEY_DOT, False, True),
    '¢': (ecodes.KEY_C, False, True),
    'æ': (ecodes.KEY_A, False, True), 'Æ': (ecodes.KEY_A, True, True),
    'ß': (ecodes.KEY_S, False, True),
}


def resolve_key(char_or_name: str) -> Optional[int]:
    c = char_or_name
    if not c:
        return None
    if c in NAMED_KEYS:
        return NAMED_KEYS[c]
    if c in CHAR_TO_KEY:
        return CHAR_TO_KEY[c]
    if c in SYMBOL_MAP:
        return SYMBOL_MAP[c]
    if c in SHIFT_MAP:
        return CHAR_TO_KEY.get(SHIFT_MAP[c]) or SYMBOL_MAP.get(SHIFT_MAP[c])
    if len(c) == 1 and 'A' <= c <= 'Z':
        return CHAR_TO_KEY.get(c.lower())
    return None


def needs_shift(char_or_name: str) -> bool:
    return char_or_name in SHIFT_MAP


class InputDevice:
    def __init__(self):
        key_caps = list(set(CHAR_TO_KEY.values()) | set(SYMBOL_MAP.values()) |
                        set(NAMED_KEYS.values()))
        key_caps.append(ecodes.KEY_102ND)

        def create_kbd():
            return UInput({
                ecodes.EV_KEY: key_caps,
            }, name="PC Remote Keyboard", version=1)

        def create_mouse():
            return UInput({
                ecodes.EV_REL: [
                    ecodes.REL_X, ecodes.REL_Y,
                    ecodes.REL_WHEEL, ecodes.REL_HWHEEL,
                ],
                ecodes.EV_KEY: [ecodes.BTN_LEFT, ecodes.BTN_RIGHT, ecodes.BTN_MIDDLE],
            }, name="PC Remote Mouse", version=1)

        with ThreadPoolExecutor(max_workers=2) as executor:
            kbd_future = executor.submit(create_kbd)
            mouse_future = executor.submit(create_mouse)
            self.kbd = kbd_future.result()
            self.mouse = mouse_future.result()

        self.modifiers_pressed = set()

    def close(self):
        self.kbd.close()
        self.mouse.close()

    def key(self, name: str, action: str):
        code = resolve_key(name)
        if code is None:
            return
        value = 1 if action == "down" else 0
        self.kbd.write(ecodes.EV_KEY, code, value)
        self.kbd.syn()

    def mouse_move(self, dx: float, dy: float):
        self.mouse.write(ecodes.EV_REL, ecodes.REL_X, int(dx))
        self.mouse.write(ecodes.EV_REL, ecodes.REL_Y, int(dy))
        self.mouse.syn()

    def mouse_button(self, button: str, action: str):
        btn_map = {"left": ecodes.BTN_LEFT, "right": ecodes.BTN_RIGHT, "middle": ecodes.BTN_MIDDLE}
        code = btn_map.get(button)
        if code is None:
            return
        value = 1 if action == "down" else 0
        self.mouse.write(ecodes.EV_KEY, code, value)
        self.mouse.syn()

    def mouse_scroll(self, dx: float, dy: float):
        if dy != 0:
            self.mouse.write(ecodes.EV_REL, ecodes.REL_WHEEL, int(dy))
            self.mouse.syn()
        if dx != 0:
            self.mouse.write(ecodes.EV_REL, ecodes.REL_HWHEEL, int(dx))
            self.mouse.syn()

    def type_text(self, text: str):
        for ch in text:
            entry = ITALIAN_CHAR_MAP.get(ch)
            if entry is None:
                self._type_unicode(ch)
                continue
            code = entry[0]
            shift = entry[1] if len(entry) >= 2 else False
            altgr = entry[2] if len(entry) >= 3 else False

            if altgr:
                self.kbd.write(ecodes.EV_KEY, ecodes.KEY_RIGHTALT, 1)
                self.kbd.syn()
            if shift:
                self.kbd.write(ecodes.EV_KEY, ecodes.KEY_LEFTSHIFT, 1)
                self.kbd.syn()
            self.kbd.write(ecodes.EV_KEY, code, 1)
            self.kbd.write(ecodes.EV_KEY, code, 0)
            self.kbd.syn()
            if shift:
                self.kbd.write(ecodes.EV_KEY, ecodes.KEY_LEFTSHIFT, 0)
                self.kbd.syn()
            if altgr:
                self.kbd.write(ecodes.EV_KEY, ecodes.KEY_RIGHTALT, 0)
                self.kbd.syn()

    def _type_unicode(self, ch: str):
        cp = ord(ch)
        hex_digits = format(cp, 'X')
        self.kbd.write(ecodes.EV_KEY, ecodes.KEY_LEFTCTRL, 1)
        self.kbd.write(ecodes.EV_KEY, ecodes.KEY_LEFTSHIFT, 1)
        self.kbd.syn()
        self.kbd.write(ecodes.EV_KEY, ecodes.KEY_U, 1)
        self.kbd.write(ecodes.EV_KEY, ecodes.KEY_U, 0)
        self.kbd.syn()
        self.kbd.write(ecodes.EV_KEY, ecodes.KEY_LEFTCTRL, 0)
        self.kbd.write(ecodes.EV_KEY, ecodes.KEY_LEFTSHIFT, 0)
        self.kbd.syn()

        hex_key_map = {
            '0': ecodes.KEY_0, '1': ecodes.KEY_1, '2': ecodes.KEY_2,
            '3': ecodes.KEY_3, '4': ecodes.KEY_4, '5': ecodes.KEY_5,
            '6': ecodes.KEY_6, '7': ecodes.KEY_7, '8': ecodes.KEY_8,
            '9': ecodes.KEY_9, 'A': ecodes.KEY_A, 'B': ecodes.KEY_B,
            'C': ecodes.KEY_C, 'D': ecodes.KEY_D, 'E': ecodes.KEY_E,
            'F': ecodes.KEY_F,
        }
        for d in hex_digits:
            key = hex_key_map.get(d)
            if key is None:
                continue
            self.kbd.write(ecodes.EV_KEY, key, 1)
            self.kbd.write(ecodes.EV_KEY, key, 0)
            self.kbd.syn()

        self.kbd.write(ecodes.EV_KEY, ecodes.KEY_ENTER, 1)
        self.kbd.write(ecodes.EV_KEY, ecodes.KEY_ENTER, 0)
        self.kbd.syn()


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def print_qr_code(data: str):
    import subprocess
    try:
        result = subprocess.run(
            ["qrencode", "-t", "UTF8", data],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            print()
            for line in result.stdout.strip().split("\n"):
                print(f"  {line}")
            print()
        else:
            raise FileNotFoundError
    except Exception:
        pass


def get_volume() -> dict:
    try:
        r = subprocess.run(
            ["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
            capture_output=True, text=True, timeout=3
        )
        m = re.search(r'(\d+)%', r.stdout)
        vol = int(m.group(1)) if m else 50
    except Exception:
        vol = 50

    try:
        r = subprocess.run(
            ["pactl", "get-sink-mute", "@DEFAULT_SINK@"],
            capture_output=True, text=True, timeout=3
        )
        muted = "yes" in r.stdout.lower() or "sì" in r.stdout.lower()
    except Exception:
        muted = False

    return {"volume": vol, "muted": muted}


def set_volume(vol: int):
    try:
        vol = max(0, min(100, int(vol)))
        subprocess.run(
            ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{vol}%"],
            capture_output=True, timeout=3
        )
    except Exception:
        pass


def toggle_mute() -> bool:
    try:
        subprocess.run(
            ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"],
            capture_output=True, timeout=3
        )
        return get_volume()["muted"]
    except Exception:
        return False


async def handle_client(websocket, input_dev: InputDevice):
    client_addr = websocket.remote_address
    print(f"  Client connected: {client_addr}")
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("t", "")
            try:
                if msg_type == "m":
                    input_dev.mouse_move(
                        data.get("x", 0),
                        data.get("y", 0),
                    )
                elif msg_type == "md":
                    input_dev.mouse_button(data.get("b", "left"), "down")
                elif msg_type == "mu":
                    input_dev.mouse_button(data.get("b", "left"), "up")
                elif msg_type == "s":
                    input_dev.mouse_scroll(
                        data.get("x", 0),
                        data.get("y", 0),
                    )
                elif msg_type == "kd":
                    name = data.get("c", "")
                    if needs_shift(name):
                        input_dev.key("KEY_LEFTSHIFT", "down")
                    input_dev.key(name, "down")
                    if needs_shift(name):
                        input_dev.key("KEY_LEFTSHIFT", "up")
                elif msg_type == "ku":
                    input_dev.key(data.get("c", ""), "up")
                elif msg_type == "kt":
                    name = data.get("c", "")
                    shift = needs_shift(name)
                    if shift:
                        input_dev.key("KEY_LEFTSHIFT", "down")
                    input_dev.key(name, "down")
                    input_dev.key(name, "up")
                    if shift:
                        input_dev.key("KEY_LEFTSHIFT", "up")
                elif msg_type == "tx":
                    input_dev.type_text(data.get("tx", ""))
                elif msg_type == "vg":
                    await websocket.send(json.dumps({
                        "t": "vs", "f": "vg", "v": get_volume()["volume"],
                        "m": get_volume()["muted"]
                    }))
                elif msg_type == "vs":
                    set_volume(data.get("v", 50))
                    await websocket.send(json.dumps({
                        "t": "vs", "f": "vs", "v": get_volume()["volume"],
                        "m": get_volume()["muted"]
                    }))
                elif msg_type == "vm":
                    toggle_mute()
                    await websocket.send(json.dumps({
                        "t": "vs", "f": "vm", "v": get_volume()["volume"],
                        "m": get_volume()["muted"]
                    }))
            except Exception as e:
                print(f"  Error processing message: {e}")
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        print(f"  Client disconnected: {client_addr}")


async def main():
    parser = argparse.ArgumentParser(description="PC Remote companion server")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket port")
    parser.add_argument("--no-uinput", action="store_true",
                        help="Run without uinput (testing mode)")
    args = parser.parse_args()

    if args.no_uinput:
        print("=" * 50)
        print("  PC Remote Server (TEST MODE - no input simulation)")
        print("=" * 50)
        input_dev = None
    else:
        try:
            print("Initialising input devices...", flush=True)
            input_dev = InputDevice()
            print("Input devices ready.", flush=True)
        except PermissionError:
            print("ERROR: Permission denied accessing /dev/uinput.")
            print("Run: sudo modprobe uinput")
            print("Then add your user to the 'input' group:")
            print("  sudo usermod -aG input $USER")
            print("  (log out and back in)")
            sys.exit(1)

    local_ip = get_local_ip()
    print("=" * 50)
    print("  PC Remote Server")
    print("=" * 50)
    url = f"ws://{local_ip}:{args.port}"
    print(f"  Listening on: {url}")
    print(f"  Enter this in the Android app:")
    print(f"    IP: {local_ip}")
    print(f"    Port: {args.port}")
    print("=" * 50)

    try:
        print_qr_code(url)
    except Exception:
        print("  (QR code generation failed - scan not available)")

    stop = asyncio.Future()

    async def handler(ws):
        await handle_client(ws, input_dev)

    async with serve(handler, "0.0.0.0", args.port):
        print("  Server running. Press Ctrl+C to stop.")
        try:
            await stop
        except asyncio.CancelledError:
            pass

    if input_dev:
        input_dev.close()
    print("Server stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down...")
