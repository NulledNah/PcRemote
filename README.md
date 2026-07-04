# PcRemote

Control your PC's mouse and keyboard from your Android phone over WiFi. Your phone becomes a trackpad + keyboard. No Bluetooth, no installation — just scan a QR code.

<p align="center">
  <img src="https://img.shields.io/badge/version-v2.0.0-%237F5A49" alt="Version">
  <img src="https://img.shields.io/badge/Windows-10%2F11-%236B493A" alt="Windows">
  <img src="https://img.shields.io/badge/Linux-Fedora%2FWayland-%236B493A" alt="Linux">
  <img src="https://img.shields.io/badge/Android-8.0%2B-%236B493A" alt="Android">
</p>

---

## Quick start

### Windows
1. Download `PcRemoteServer.exe` from the [latest Release](https://github.com/NulledNah/PcRemote/releases)
2. Double-click it — the server starts silently in your system tray
3. Right-click the tray icon → **Show Dashboard** → scan the QR code with the Android app

No Python required. The `.exe` bundles everything.

### Linux
```bash
git clone https://github.com/NulledNah/PcRemote.git
cd PcRemote/companion
# Fedora: sudo dnf install -y kernel-headers
# Ubuntu/Debian: sudo apt install -y linux-headers-$(uname -r)
sudo modprobe uinput
pip install -r requirements.txt -r requirements-linux.txt
python3 server.py
```

---

## Features

**v2 (current — `v2` branch):**

| Feature | Windows | Linux |
|---|---|---|
| System tray with dashboard | ✓ | — |
| QR code on demand (dashboard) | ✓ | ✓ (terminal) |
| Adaptive mouse flush (2ms) | ✓ | ✓ |
| Volume sync (Core Audio / PulseAudio) | ✓ | ✓ |
| Structured logging (file) | ✓ | ✓ |
| Diagnostic wizard (firewall, port) | ✓ | ✓ |
| Standalone `.exe` build | ✓ | — |

**v1 (stable — `main` branch):**

| Feature | Linux |
|---|---|
| Terminal-based server | ✓ |
| Trackpad + keyboard | ✓ |
| QR code (qrencode) | ✓ |
| Volume control (pactl) | ✓ |

---

## How it works

1. Run the server on your PC — it starts a WebSocket server on your local network
2. Open the Android app, scan the QR code from the dashboard
3. Your phone is now a trackpad and keyboard for the PC

Everything goes over your local WiFi. On Linux the server uses `uinput` for kernel-level input simulation. On Windows it uses Win32 `SendInput`.

---

## Requirements

| | Linux | Windows |
|---|---|---|
| **Python** | 3.x | Not needed (`.exe` bundles it) |
| **Dependencies** | `pip install -r requirements.txt -r requirements-linux.txt` | Bundled in `.exe` |
| **uinput** | `sudo modprobe uinput` + `input` group | N/A |
| **Firewall** | Typically open | Auto-fixed or manual rule |

**Phone:** Android 8.0+ with PcRemote APK installed.

---

## Project structure

```
PcRemote/
├── companion/
│   ├── server.py              # Entry point
│   ├── run.bat                # Windows launcher
│   ├── build.py               # PyInstaller build
│   ├── requirements.txt        # Common deps
│   ├── requirements-linux.txt  # Linux-only (evdev)
│   ├── requirements-windows.txt # Windows-only (pycaw, pystray)
│   ├── icon.ico               # App icon
│   └── pcremote/              # Backend package
│       ├── backends/
│       │   ├── base.py        # Abstract backends
│       │   ├── linux.py       # uinput + pactl
│       │   ├── windows.py     # SendInput + Core Audio
│       │   └── qr.py          # QR code (tkinter/PIL)
│       ├── protocol.py        # WebSocket message types
│       ├── config.py          # Persistent settings
│       ├── logsetup.py        # Structured logging
│       ├── diagnostics.py     # Startup checks
│       └── tray.py            # Windows tray + dashboard
├── android/                   # Android app (Kotlin + Jetpack Compose)
└── app icon/
```

---

## Building from source

```bash
# Windows
cd companion
pip install -r requirements.txt -r requirements-windows.txt pyinstaller
python build.py                    # → dist/PcRemoteServer.exe

# Linux
cd companion
pip install -r requirements.txt -r requirements-linux.txt
python3 server.py                  # run directly
```

---

## Branches

| Branch | Status | Description |
|---|---|---|
| `main` | Stable v1.x | Linux-only, proven on Fedora 44 |
| `v2` | Experimental v2.0 | Cross-platform (Windows + Linux) |

---

## Notes

- First run on Android 13+ asks for notification permission (for the connection notification)
- `uinput` devices take a few seconds to initialize on some kernels
- Windows Firewall may prompt on first run — the diagnostic wizard auto-fixes it
- Running as Administrator on Windows may prevent SendInput from working — run as normal user

---

## License

MIT
