import subprocess
import re
import queue
import threading
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from evdev import UInput, ecodes, AbsInfo

from .base import InputBackend, VolumeBackend


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
    'KEY_LEFTCTRL': ecodes.KEY_LEFTCTRL, 'KEY_RIGHTCTRL': ecodes.KEY_RIGHTCTRL,
    'KEY_LEFTALT': ecodes.KEY_LEFTALT, 'KEY_RIGHTALT': ecodes.KEY_RIGHTALT,
    'KEY_LEFTMETA': ecodes.KEY_LEFTMETA, 'KEY_RIGHTMETA': ecodes.KEY_RIGHTMETA,
    'KEY_LEFTSHIFT': ecodes.KEY_LEFTSHIFT, 'KEY_RIGHTSHIFT': ecodes.KEY_RIGHTSHIFT,
    'KEY_UP': ecodes.KEY_UP, 'KEY_DOWN': ecodes.KEY_DOWN,
    'KEY_LEFT': ecodes.KEY_LEFT, 'KEY_RIGHT': ecodes.KEY_RIGHT,
    'KEY_TAB': ecodes.KEY_TAB, 'KEY_ESC': ecodes.KEY_ESC,
    'KEY_ENTER': ecodes.KEY_ENTER, 'KEY_BACKSPACE': ecodes.KEY_BACKSPACE,
    'KEY_DELETE': ecodes.KEY_DELETE, 'KEY_SPACE': ecodes.KEY_SPACE,
    'KEY_HOME': ecodes.KEY_HOME, 'KEY_END': ecodes.KEY_END,
    'KEY_PAGEUP': ecodes.KEY_PAGEUP, 'KEY_PAGEDOWN': ecodes.KEY_PAGEDOWN,
    'KEY_INSERT': ecodes.KEY_INSERT, 'KEY_CAPSLOCK': ecodes.KEY_CAPSLOCK,
    'KEY_NUMLOCK': ecodes.KEY_NUMLOCK, 'KEY_SCROLLLOCK': ecodes.KEY_SCROLLLOCK,
    'KEY_F1': ecodes.KEY_F1, 'KEY_F2': ecodes.KEY_F2,
    'KEY_F3': ecodes.KEY_F3, 'KEY_F4': ecodes.KEY_F4,
    'KEY_F5': ecodes.KEY_F5, 'KEY_F6': ecodes.KEY_F6,
    'KEY_F7': ecodes.KEY_F7, 'KEY_F8': ecodes.KEY_F8,
    'KEY_F9': ecodes.KEY_F9, 'KEY_F10': ecodes.KEY_F10,
    'KEY_F11': ecodes.KEY_F11, 'KEY_F12': ecodes.KEY_F12,
    'KEY_PRINT': ecodes.KEY_SYSRQ, 'KEY_PAUSE': ecodes.KEY_PAUSE,
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


class LinuxUinputBackend(InputBackend):
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

        self._queue = queue.Queue()
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    def _worker_loop(self):
        while True:
            job = self._queue.get()
            if job is None:
                break
            try:
                job()
            except Exception:
                pass

    def close(self):
        self._queue.put(None)
        self._worker.join(timeout=2)
        self.kbd.close()
        self.mouse.close()

    def _write_key(self, code, value):
        self.kbd.write(ecodes.EV_KEY, code, value)
        self.kbd.syn()

    def key(self, name: str, action: str):
        code = resolve_key(name)
        if code is None:
            return
        value = 1 if action == "down" else 0
        self._queue.put(lambda c=code, v=value: self._write_key(c, v))

    def mouse_move(self, dx: float, dy: float):
        ix = int(dx)
        iy = int(dy)
        if ix == 0 and iy == 0:
            return
        self._queue.put(lambda: (
            self.mouse.write(ecodes.EV_REL, ecodes.REL_X, ix),
            self.mouse.write(ecodes.EV_REL, ecodes.REL_Y, iy),
            self.mouse.syn(),
        ))

    def mouse_button(self, button: str, action: str):
        btn_map = {"left": ecodes.BTN_LEFT, "right": ecodes.BTN_RIGHT, "middle": ecodes.BTN_MIDDLE}
        code = btn_map.get(button)
        if code is None:
            return
        value = 1 if action == "down" else 0
        self._queue.put(lambda c=code, v=value: (
            self.mouse.write(ecodes.EV_KEY, c, v),
            self.mouse.syn(),
        ))

    def mouse_scroll(self, dx: float, dy: float):
        ix = int(dx)
        iy = int(dy)
        if ix == 0 and iy == 0:
            return
        self._queue.put(lambda x=ix, y=iy: self._scroll_impl(x, y))

    def _scroll_impl(self, dx: int, dy: int):
        if dy != 0:
            self.mouse.write(ecodes.EV_REL, ecodes.REL_WHEEL, dy)
            self.mouse.syn()
        if dx != 0:
            self.mouse.write(ecodes.EV_REL, ecodes.REL_HWHEEL, dx)
            self.mouse.syn()

    def type_text(self, text: str):
        if not text:
            return
        self._queue.put(lambda t=text: self._type_text_impl(t))

    def _type_text_impl(self, text: str):
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


class LinuxPactlBackend(VolumeBackend):
    @property
    def supports_precise_volume(self) -> bool:
        return True

    def get_volume(self) -> dict:
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

    def set_volume(self, vol: int):
        try:
            vol = max(0, min(100, int(vol)))
            subprocess.run(
                ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{vol}%"],
                capture_output=True, timeout=3
            )
        except Exception:
            pass

    def toggle_mute(self) -> bool:
        try:
            subprocess.run(
                ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"],
                capture_output=True, timeout=3
            )
            return self.get_volume()["muted"]
        except Exception:
            return False
