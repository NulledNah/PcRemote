#!/usr/bin/env python3
"""PyInstaller build script for PcRemote Server (Windows)."""

import os
import subprocess
import sys

COMPANION_DIR = os.path.dirname(os.path.abspath(__file__))


def build():
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "pyinstaller"],
        check=True,
        cwd=COMPANION_DIR,
    )

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--noconsole",
        "--name", "PcRemoteServer",
        "--add-data", f"pcremote{os.pathsep}pcremote",
        "--add-data", f"icon.ico{os.pathsep}.",
        "--icon", "icon.ico",
        "--hidden-import", "websockets",
        "--hidden-import", "qrcode",
        "--hidden-import", "qrcode.image.pil",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL.ImageTk",
        "--hidden-import", "tkinter",
        "--hidden-import", "pycaw",
        "--hidden-import", "pycaw.pycaw",
        "--hidden-import", "comtypes",
        "--hidden-import", "comtypes.stream",
        "--hidden-import", "pystray",
        "--hidden-import", "pystray._win32",
        "--hidden-import", "pcremote.tray",
        "--hidden-import", "pcremote.backends.windows",
        "--hidden-import", "pcremote.backends.linux",
        "--clean",
        "--noconfirm",
        "server.py",
    ]

    print("[BUILD] Running PyInstaller...")
    subprocess.run(cmd, check=True, cwd=COMPANION_DIR)
    print("[BUILD] Done! Executable: companion/dist/PcRemoteServer.exe")


if __name__ == "__main__":
    build()
