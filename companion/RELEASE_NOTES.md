## PcRemote v2.0.0 (stable)

First cross-platform release. Windows support with native system tray, dashboard, and standalone `.exe`. Linux support preserved from v1.

### What's new

**Windows support**
- System tray icon with right-click menu
- Dashboard with QR code, connection URL, and live logs
- Standalone `.exe` — no Python required
- Win32 SendInput for keyboard/mouse simulation
- Windows Core Audio API for real-time volume sync

**Cross-platform improvements**
- Adaptive mouse flush (event-driven, 2ms min interval)
- Sub-pixel accumulation for smooth cursor movement
- Optional authentication token (`--password`)
- Structured logging to file (`%APPDATA%\PcRemote\`)
- Startup diagnostic wizard (firewall, port, audio checks)

**Linux**
- All v1 features preserved
- QR code via terminal or generated PNG

### Installation

**Windows:** Download `PcRemoteServer.exe` below. Double-click to run. The server starts in the system tray.

**Linux:** `pip install -r requirements.txt -r requirements-linux.txt && python3 server.py`

### SHA256

```
PcRemoteServer.exe
25C25B05F559B37706ADECE6C172CB072BCF002CA918EC1994B95F64580A67BA
```

### Known limitations

- Dashboard uses tkinter (included in exe, no extra install)
- System tray requires pystray + PIL (bundled in exe)
- Windows Defender may flag the unsigned `.exe` — this is a false positive common to all PyInstaller-built executables

---

**Full Changelog**: https://github.com/NulledNah/PcRemote/compare/main...v2
