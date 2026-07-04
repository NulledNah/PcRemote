import ctypes
from ctypes import wintypes
import time
import threading
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

WHEEL_DELTA = 120

VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF


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

GetAsyncKeyState = user32.GetAsyncKeyState
GetAsyncKeyState.argtypes = [ctypes.c_int]
GetAsyncKeyState.restype = wintypes.SHORT

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


def _send_key_input(vk: int, flags: int = 0, scan: int = 0):
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki.wVk = vk
    inp.ki.wScan = scan
    inp.ki.dwFlags = flags
    inp.ki.time = 0
    inp.ki.dwExtraInfo = None
    SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def _send_mouse_input(flags: int, dx: int = 0, dy: int = 0, data: int = 0):
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.mi.dx = dx
    inp.mi.dy = dy
    inp.mi.mouseData = data
    inp.mi.dwFlags = flags
    inp.mi.time = 0
    inp.mi.dwExtraInfo = None
    SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def resolve_key(name: str) -> Optional[int]:
    return VK_MAP.get(name)


def needs_shift(name: str) -> bool:
    return name in SHIFT_REQUIRED


class WindowsSendInputBackend(InputBackend):
    def __init__(self):
        self.modifiers_pressed = set()
        self._lock = threading.Lock()

    def close(self):
        for mod in list(self.modifiers_pressed):
            self.key(mod, "up")

    def key(self, name: str, action: str):
        vk = resolve_key(name)
        if vk is None:
            return
        with self._lock:
            if action == "down":
                self.modifiers_pressed.add(name)
                _send_key_input(vk, 0)
            else:
                self.modifiers_pressed.discard(name)
                _send_key_input(vk, KEYEVENTF_KEYUP)

    def mouse_move(self, dx: float, dy: float):
        with self._lock:
            _send_mouse_input(MOUSEEVENTF_MOVE, int(dx), int(dy))

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
        with self._lock:
            _send_mouse_input(flag)

    def mouse_scroll(self, dx: float, dy: float):
        with self._lock:
            if dy != 0:
                _send_mouse_input(MOUSEEVENTF_WHEEL, data=int(dy) * WHEEL_DELTA)
            if dx != 0:
                _send_mouse_input(MOUSEEVENTF_HWHEEL, data=int(dx) * WHEEL_DELTA)

    def type_text(self, text: str):
        with self._lock:
            for ch in text:
                cp = ord(ch)
                if cp == 0x0D or cp == 0x0A:
                    _send_key_input(0x0D)
                    _send_key_input(0x0D, KEYEVENTF_KEYUP)
                    continue
                if cp == 0x09:
                    _send_key_input(0x09)
                    _send_key_input(0x09, KEYEVENTF_KEYUP)
                    continue
                if cp == 0x08:
                    _send_key_input(0x08)
                    _send_key_input(0x08, KEYEVENTF_KEYUP)
                    continue
                inp = INPUT()
                inp.type = INPUT_KEYBOARD
                inp.ki.wVk = 0
                inp.ki.wScan = cp
                inp.ki.dwFlags = KEYEVENTF_UNICODE
                inp.ki.time = 0
                inp.ki.dwExtraInfo = None
                SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

                inp_up = INPUT()
                inp_up.type = INPUT_KEYBOARD
                inp_up.ki.wVk = 0
                inp_up.ki.wScan = cp
                inp_up.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
                inp_up.ki.time = 0
                inp_up.ki.dwExtraInfo = None
                SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))


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
            _send_key_input(vk)
            _send_key_input(vk, KEYEVENTF_KEYUP)
            time.sleep(0.01)

    def toggle_mute(self) -> bool:
        _send_key_input(VK_VOLUME_MUTE)
        _send_key_input(VK_VOLUME_MUTE, KEYEVENTF_KEYUP)
        self._muted = not self._muted
        return self._muted
