import ctypes
from ctypes import wintypes
import time
from typing import Optional

from .base import InputBackend, VolumeBackend

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

INPUT_KEYBOARD = 1
INPUT_MOUSE = 0

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x01000
MOUSEEVENTF_ABSOLUTE = 0x8000

WHEEL_DELTA = 120

VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF

SPI_GETMOUSE = 0x0003
SPI_SETMOUSE = 0x0004
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02

BATCH_INTERVAL = 0.002
BATCH_MAX_SIZE = 64


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

MapVirtualKeyW = user32.MapVirtualKeyW
MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
MapVirtualKeyW.restype = wintypes.UINT

SystemParametersInfoW = user32.SystemParametersInfoW
SystemParametersInfoW.argtypes = [wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT]
SystemParametersInfoW.restype = wintypes.BOOL

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


def resolve_key(name: str) -> Optional[int]:
    return VK_MAP.get(name)


def needs_shift(name: str) -> bool:
    return name in SHIFT_REQUIRED


class WindowsSendInputBackend(InputBackend):
    def __init__(self, disable_accel: bool = True):
        self.modifiers_pressed = set()
        self._batch = []
        self._last_flush = time.monotonic()
        self._prev_mouse_accel = None
        if disable_accel:
            self._disable_mouse_accel()

    def close(self):
        self._flush_batch()
        self._restore_mouse_accel()
        for mod in list(self.modifiers_pressed):
            self.key(mod, "up")

    def _disable_mouse_accel(self):
        try:
            accel = ctypes.c_int(0)
            params = (ctypes.c_int * 3)()
            if SystemParametersInfoW(SPI_GETMOUSE, 0, params, 0):
                self._prev_mouse_accel = tuple(params)
            if SystemParametersInfoW(SPI_SETMOUSE, 0, params, SPIF_SENDCHANGE):
                params[2] = 0
                SystemParametersInfoW(SPI_SETMOUSE, 0, params, SPIF_SENDCHANGE)
        except Exception:
            pass

    def _restore_mouse_accel(self):
        if self._prev_mouse_accel is None:
            return
        try:
            params = (ctypes.c_int * 3)(*self._prev_mouse_accel)
            SystemParametersInfoW(SPI_SETMOUSE, 0, params, SPIF_SENDCHANGE)
        except Exception:
            pass

    def _flush_batch(self):
        if not self._batch:
            return
        n = len(self._batch)
        arr = (INPUT * n)(*self._batch)
        SendInput(n, ctypes.byref(arr), ctypes.sizeof(INPUT))
        self._batch.clear()
        self._last_flush = time.monotonic()

    def _add_mouse_input(self, flags: int, dx: int = 0, dy: int = 0, data: int = 0):
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.mi.dx = dx
        inp.mi.dy = dy
        inp.mi.mouseData = data
        inp.mi.dwFlags = flags
        inp.mi.time = 0
        inp.mi.dwExtraInfo = None
        self._batch.append(inp)

    def _maybe_flush(self, force: bool = False):
        now = time.monotonic()
        if force or len(self._batch) >= BATCH_MAX_SIZE or (now - self._last_flush) >= BATCH_INTERVAL:
            self._flush_batch()

    def key(self, name: str, action: str):
        vk = resolve_key(name)
        if vk is None:
            return
        self._maybe_flush(force=True)
        if action == "down":
            self.modifiers_pressed.add(name)
            inp = INPUT()
            inp.type = INPUT_KEYBOARD
            inp.ki.wVk = vk
            inp.ki.wScan = 0
            inp.ki.dwFlags = 0
            inp.ki.time = 0
            inp.ki.dwExtraInfo = None
            SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        else:
            self.modifiers_pressed.discard(name)
            inp = INPUT()
            inp.type = INPUT_KEYBOARD
            inp.ki.wVk = vk
            inp.ki.wScan = 0
            inp.ki.dwFlags = KEYEVENTF_KEYUP
            inp.ki.time = 0
            inp.ki.dwExtraInfo = None
            SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def mouse_move(self, dx: float, dy: float):
        idx = int(dx)
        idy = int(dy)
        if idx == 0 and idy == 0:
            return
        self._add_mouse_input(MOUSEEVENTF_MOVE, idx, idy)
        self._maybe_flush()

    def mouse_button(self, button: str, action: str):
        flags = {
            ("left", "down"): MOUSEEVENTF_LEFTDOWN,
            ("left", "up"): MOUSEEVENTF_LEFTUP,
            ("right", "down"): MOUSEEVENTF_RIGHTDOWN,
            ("right", "up"): MOUSEEVENTF_RIGHTUP,
            ("middle", "down"): MOUSEEVENTF_MIDDLEDOWN,
            ("middle", "up"): MOUSEEVENTF_MIDDLEUP,
        }
        flag = flags.get((button, action))
        if flag is None:
            return
        self._maybe_flush(force=True)
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.mi.dx = 0
        inp.mi.dy = 0
        inp.mi.mouseData = 0
        inp.mi.dwFlags = flag
        inp.mi.time = 0
        inp.mi.dwExtraInfo = None
        SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def mouse_scroll(self, dx: float, dy: float):
        self._maybe_flush(force=True)
        if dy != 0:
            inp = INPUT()
            inp.type = INPUT_MOUSE
            inp.mi.dx = 0
            inp.mi.dy = 0
            inp.mi.mouseData = int(dy) * WHEEL_DELTA
            inp.mi.dwFlags = MOUSEEVENTF_WHEEL
            inp.mi.time = 0
            inp.mi.dwExtraInfo = None
            SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        if dx != 0:
            inp = INPUT()
            inp.type = INPUT_MOUSE
            inp.mi.dx = 0
            inp.mi.dy = 0
            inp.mi.mouseData = int(dx) * WHEEL_DELTA
            inp.mi.dwFlags = MOUSEEVENTF_HWHEEL
            inp.mi.time = 0
            inp.mi.dwExtraInfo = None
            SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def type_text(self, text: str):
        self._maybe_flush(force=True)
        for ch in text:
            cp = ord(ch)
            if cp == 0x0D or cp == 0x0A:
                inp = INPUT()
                inp.type = INPUT_KEYBOARD
                inp.ki.wVk = 0x0D
                inp.ki.wScan = 0
                inp.ki.dwFlags = 0
                inp.ki.time = 0
                inp.ki.dwExtraInfo = None
                SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
                inp.ki.dwFlags = KEYEVENTF_KEYUP
                SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
                continue
            if cp == 0x09:
                inp = INPUT()
                inp.type = INPUT_KEYBOARD
                inp.ki.wVk = 0x09
                inp.ki.wScan = 0
                inp.ki.dwFlags = 0
                inp.ki.time = 0
                inp.ki.dwExtraInfo = None
                SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
                inp.ki.dwFlags = KEYEVENTF_KEYUP
                SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
                continue
            if cp == 0x08:
                inp = INPUT()
                inp.type = INPUT_KEYBOARD
                inp.ki.wVk = 0x08
                inp.ki.wScan = 0
                inp.ki.dwFlags = 0
                inp.ki.time = 0
                inp.ki.dwExtraInfo = None
                SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
                inp.ki.dwFlags = KEYEVENTF_KEYUP
                SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
                continue
            inp = INPUT()
            inp.type = INPUT_KEYBOARD
            inp.ki.wVk = 0
            inp.ki.wScan = cp
            inp.ki.dwFlags = KEYEVENTF_UNICODE
            inp.ki.time = 0
            inp.ki.dwExtraInfo = None
            SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

            inp.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
            SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


class WindowsVolumeBackend(VolumeBackend):
    def __init__(self):
        self._vol = 50
        self._muted = False

    @property
    def supports_precise_volume(self) -> bool:
        return False

    def get_volume(self) -> dict:
        return {"volume": self._vol, "muted": self._muted}

    def set_volume(self, vol: int):
        vol = max(0, min(100, int(vol)))
        diff = vol - self._vol
        self._vol = vol
        vk = VK_VOLUME_UP if diff > 0 else VK_VOLUME_DOWN
        steps = min(abs(diff) // 2, 50)
        for _ in range(steps):
            inp = INPUT()
            inp.type = INPUT_KEYBOARD
            inp.ki.wVk = vk
            inp.ki.wScan = 0
            inp.ki.dwFlags = 0
            inp.ki.time = 0
            inp.ki.dwExtraInfo = None
            SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
            inp.ki.dwFlags = KEYEVENTF_KEYUP
            SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
            time.sleep(0.01)

    def toggle_mute(self) -> bool:
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.ki.wVk = VK_VOLUME_MUTE
        inp.ki.wScan = 0
        inp.ki.dwFlags = 0
        inp.ki.time = 0
        inp.ki.dwExtraInfo = None
        SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        inp.ki.dwFlags = KEYEVENTF_KEYUP
        SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        self._muted = not self._muted
        return self._muted
