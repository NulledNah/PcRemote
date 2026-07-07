import ctypes
from ctypes import wintypes
import time
from typing import Optional

from .base import InputBackend, VolumeBackend

user32 = ctypes.windll.user32

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x01000

WHEEL_DELTA = 120

VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF

MOUSE_BUTTONS = {
    ("left", "down"): MOUSEEVENTF_LEFTDOWN,
    ("left", "up"): MOUSEEVENTF_LEFTUP,
    ("right", "down"): MOUSEEVENTF_RIGHTDOWN,
    ("right", "up"): MOUSEEVENTF_RIGHTUP,
    ("middle", "down"): MOUSEEVENTF_MIDDLEDOWN,
    ("middle", "up"): MOUSEEVENTF_MIDDLEUP,
}

VK_MAP = {
    'KEY_LEFTCTRL': 0x11, 'KEY_RIGHTCTRL': 0x11,
    'KEY_LEFTALT': 0x12, 'KEY_RIGHTALT': 0x12,
    'KEY_LEFTSHIFT': 0x10, 'KEY_RIGHTSHIFT': 0x10,
    'KEY_LEFTMETA': 0x5B, 'KEY_RIGHTMETA': 0x5C,
    'KEY_UP': 0x26, 'KEY_DOWN': 0x28,
    'KEY_LEFT': 0x25, 'KEY_RIGHT': 0x27,
    'KEY_TAB': 0x09, 'KEY_ESC': 0x1B,
    'KEY_ENTER': 0x0D, 'KEY_BACKSPACE': 0x08,
    'KEY_DELETE': 0x2E, 'KEY_SPACE': 0x20,
    'KEY_HOME': 0x24, 'KEY_END': 0x23,
    'KEY_PAGEUP': 0x21, 'KEY_PAGEDOWN': 0x22,
    'KEY_INSERT': 0x2D, 'KEY_CAPSLOCK': 0x14,
    'KEY_NUMLOCK': 0x90, 'KEY_SCROLLLOCK': 0x91,
    'KEY_PRINT': 0x2C, 'KEY_PAUSE': 0x13,
    'KEY_F1': 0x70, 'KEY_F2': 0x71, 'KEY_F3': 0x72,
    'KEY_F4': 0x73, 'KEY_F5': 0x74, 'KEY_F6': 0x75,
    'KEY_F7': 0x76, 'KEY_F8': 0x77, 'KEY_F9': 0x78,
    'KEY_F10': 0x79, 'KEY_F11': 0x7A, 'KEY_F12': 0x7B,
    'KEY_0': 0x30, 'KEY_1': 0x31, 'KEY_2': 0x32,
    'KEY_3': 0x33, 'KEY_4': 0x34, 'KEY_5': 0x35,
    'KEY_6': 0x36, 'KEY_7': 0x37, 'KEY_8': 0x38,
    'KEY_9': 0x39,
    'KEY_A': 0x41, 'KEY_B': 0x42, 'KEY_C': 0x43,
    'KEY_D': 0x44, 'KEY_E': 0x45, 'KEY_F': 0x46,
    'KEY_G': 0x47, 'KEY_H': 0x48, 'KEY_I': 0x49,
    'KEY_J': 0x4A, 'KEY_K': 0x4B, 'KEY_L': 0x4C,
    'KEY_M': 0x4D, 'KEY_N': 0x4E, 'KEY_O': 0x4F,
    'KEY_P': 0x50, 'KEY_Q': 0x51, 'KEY_R': 0x52,
    'KEY_S': 0x53, 'KEY_T': 0x54, 'KEY_U': 0x55,
    'KEY_V': 0x56, 'KEY_W': 0x57, 'KEY_X': 0x58,
    'KEY_Y': 0x59, 'KEY_Z': 0x5A,
}

SHIFT_REQUIRED = {'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L',
                  'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X',
                  'Y', 'Z'}


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
    ]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", INPUT_UNION),
    ]


SendInput = user32.SendInput
SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
SendInput.restype = wintypes.UINT


def _send_mouse(flags: int, dx: int = 0, dy: int = 0, data: int = 0):
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.mi.dx = dx
    inp.mi.dy = dy
    inp.mi.mouseData = data
    inp.mi.dwFlags = flags
    inp.mi.time = 0
    inp.mi.dwExtraInfo = None
    SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def _send_key(vk: int, flags: int = 0, scan: int = 0):
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki.wVk = vk
    inp.ki.wScan = scan
    inp.ki.dwFlags = flags
    inp.ki.time = 0
    inp.ki.dwExtraInfo = None
    SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def resolve_key(name: str) -> Optional[int]:
    return VK_MAP.get(name)


def needs_shift(name: str) -> bool:
    return name in SHIFT_REQUIRED


class WindowsSendInputBackend(InputBackend):
    MIN_FLUSH_INTERVAL = 0.002
    SAFETY_TICK_MS = 8

    def __init__(self):
        self.modifiers_pressed = set()
        self._dx = 0.0
        self._dy = 0.0
        self._last_flush = time.monotonic()
        self._ticker_task = None
        self._debug_total = 0
        self._debug_count = 0
        self._debug_max = 0.0

    def start_ticker(self, loop):
        self._ticker_task = loop.create_task(self._safety_ticker())

    def stop_ticker(self):
        if self._ticker_task:
            self._ticker_task.cancel()
            self._ticker_task = None

    async def _safety_ticker(self):
        import asyncio
        while True:
            await asyncio.sleep(self.SAFETY_TICK_MS / 1000.0)
            if self._dx == 0.0 and self._dy == 0.0:
                continue
            now = time.monotonic()
            if now - self._last_flush >= self.MIN_FLUSH_INTERVAL:
                self._flush(now)

    def _flush(self, now: float = 0.0):
        if now == 0.0:
            now = time.monotonic()
        elapsed = now - self._last_flush
        self._last_flush = now

        dx, self._dx = self._dx, 0.0
        dy, self._dy = self._dy, 0.0
        idx = int(dx)
        idy = int(dy)
        self._dx += dx - idx
        self._dy += dy - idy
        if idx != 0 or idy != 0:
            _send_mouse(MOUSEEVENTF_MOVE, idx, idy)

        self._debug_total += elapsed
        self._debug_count += 1
        if elapsed > self._debug_max:
            self._debug_max = elapsed
        if self._debug_count % 120 == 0:
            import logging
            logging.getLogger("pcremote").debug(
                "mouse flush interval: avg=%.1fms min=%.1fms max=%.1fms count=%d",
                (self._debug_total / self._debug_count) * 1000,
                self.MIN_FLUSH_INTERVAL * 1000,
                self._debug_max * 1000,
                self._debug_count,
            )

    def close(self):
        self.stop_ticker()
        for mod in list(self.modifiers_pressed):
            self.key(mod, "up")

    def mouse_move(self, dx: float, dy: float):
        self._dx += dx
        self._dy += dy
        now = time.monotonic()
        if now - self._last_flush >= self.MIN_FLUSH_INTERVAL:
            self._flush(now)

    def mouse_button(self, button: str, action: str):
        flag = MOUSE_BUTTONS.get((button, action))
        if flag is None:
            return
        _send_mouse(flag)

    def mouse_scroll(self, dx: float, dy: float):
        if dy != 0:
            _send_mouse(MOUSEEVENTF_WHEEL, data=int(dy) * WHEEL_DELTA)
        if dx != 0:
            _send_mouse(MOUSEEVENTF_HWHEEL, data=int(dx) * WHEEL_DELTA)

    def key(self, name: str, action: str):
        vk = resolve_key(name)
        if vk is None:
            return
        if action == "down":
            self.modifiers_pressed.add(name)
            _send_key(vk)
        else:
            self.modifiers_pressed.discard(name)
            _send_key(vk, KEYEVENTF_KEYUP)

    def type_text(self, text: str):
        for ch in text:
            cp = ord(ch)
            if cp == 0x0D or cp == 0x0A:
                _send_key(0x0D)
                _send_key(0x0D, KEYEVENTF_KEYUP)
                continue
            if cp == 0x09:
                _send_key(0x09)
                _send_key(0x09, KEYEVENTF_KEYUP)
                continue
            if cp == 0x08:
                _send_key(0x08)
                _send_key(0x08, KEYEVENTF_KEYUP)
                continue
            _send_key(0, KEYEVENTF_UNICODE, cp)
            _send_key(0, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, cp)


class WindowsVolumeBackend(VolumeBackend):
    def __init__(self):
        self._endpoint = None
        try:
            from pycaw.pycaw import AudioUtilities
            devices = AudioUtilities.GetSpeakers()
            if devices is None:
                raise RuntimeError("No audio output device found")
            self._endpoint = devices.EndpointVolume
            self._endpoint.GetMasterVolumeLevelScalar()
            import logging
            logging.getLogger("pcremote").debug(
                "Windows Core Audio volume backend ready"
            )
        except Exception:
            import logging
            logging.getLogger("pcremote").warning(
                "Core Audio init failed, falling back to media key volume"
            )

    @property
    def supports_precise_volume(self) -> bool:
        return self._endpoint is not None

    def get_volume(self) -> dict:
        if self._endpoint is not None:
            try:
                vol = self._endpoint.GetMasterVolumeLevelScalar()
                muted = self._endpoint.GetMute()
                return {"volume": int(vol * 100), "muted": bool(muted)}
            except Exception:
                pass
        return {"volume": 50, "muted": False}

    def set_volume(self, vol: int):
        vol = max(0, min(100, int(vol)))
        if self._endpoint is not None:
            try:
                self._endpoint.SetMasterVolumeLevelScalar(vol / 100.0, None)
                return
            except Exception:
                pass
        diff = vol - self.get_volume()["volume"]
        vk = VK_VOLUME_UP if diff > 0 else VK_VOLUME_DOWN
        steps = min(abs(diff) // 2, 50)
        for _ in range(steps):
            _send_key(vk)
            _send_key(vk, KEYEVENTF_KEYUP)
            time.sleep(0.01)

    def toggle_mute(self) -> bool:
        if self._endpoint is not None:
            try:
                current = self._endpoint.GetMute()
                self._endpoint.SetMute(not current, None)
                return not current
            except Exception:
                pass
        _send_key(VK_VOLUME_MUTE)
        _send_key(VK_VOLUME_MUTE, KEYEVENTF_KEYUP)
        return not self.get_volume()["muted"]
