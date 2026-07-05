# Contributing

## Project structure

```
companion/          Python server
  server.py         Entry point
  build.py          PyInstaller build script
  pcremote/
    backends/       Windows (SendInput + Core Audio) and Linux (uinput + pactl)
    protocol.py     WebSocket message types
    diagnostics.py  Firewall and port checks
    tray.py         Windows system tray + tkinter Dashboard
    config.py       Persistent settings
android/            Android app (Kotlin + Jetpack Compose)
  app/src/main/java/com/example/pcremote/
    ui/             Screens (connection, remote, trackpad, keyboard)
    viewmodel/      RemoteViewModel
    network/        WebSocket client + message types
```

## Building the server

```
# Windows
cd companion
pip install -r requirements.txt -r requirements-windows.txt pyinstaller
python build.py

# Linux
pip install -r requirements.txt -r requirements-linux.txt
python3 server.py
```

## Building the Android app

```
# Requires Android SDK
cd android
echo sdk.dir=/path/to/Android/Sdk > local.properties
./gradlew assembleDebug
```

## Protocol

The server and app communicate over a WebSocket at `ws://<host>:8765`.
Messages are JSON with a `"t"` field indicating the type.

See `companion/pcremote/protocol.py` for the full message catalog.
