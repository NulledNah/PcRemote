#!/usr/bin/env python3
"""PC Remote companion server - cross-platform (Linux + Windows).

Receives commands via WebSocket and simulates keyboard/mouse input.
Run: python3 server.py [--port PORT] [--password PASSWORD]
"""

import argparse
import asyncio
import json
import os
import socket
import sys
import time
from typing import Optional

import websockets
from websockets.asyncio.server import serve

from pcremote import VERSION, PROTOCOL_VERSION
from pcremote.backends.base import InputBackend, VolumeBackend
from pcremote.backends.qr import QrBackends
from pcremote.config import load_config, get_or_create_token
from pcremote.logsetup import setup as setup_logging, get as get_logger
from pcremote.diagnostics import run_diagnostics, auto_fix_firewall
from pcremote.protocol import (
    MSG_MOUSE_MOVE, MSG_MOUSE_DOWN, MSG_MOUSE_UP, MSG_MOUSE_SCROLL,
    MSG_KEY_DOWN, MSG_KEY_UP, MSG_KEY_TAP, MSG_TYPE_TEXT,
    MSG_VOLUME_GET, MSG_VOLUME_SET, MSG_VOLUME_MUTE, MSG_AUTH, MSG_PING, MSG_PONG,
    decode_message,
)


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def create_input_backend(disable_mouse_accel: bool = True) -> InputBackend:
    if os.name == 'nt':
        from pcremote.backends.windows import WindowsSendInputBackend
        return WindowsSendInputBackend(disable_accel=disable_mouse_accel)
    else:
        return LinuxUinputBackend()


def create_volume_backend() -> VolumeBackend:
    if os.name == 'nt':
        from pcremote.backends.windows import WindowsVolumeBackend
        return WindowsVolumeBackend()
    else:
        return LinuxPactlBackend()


def get_key_resolver():
    if os.name == 'nt':
        from pcremote.backends.windows import resolve_key as rk, needs_shift as ns
        return rk, ns
    else:
        from pcremote.backends.linux import resolve_key as rk, needs_shift as ns
        return rk, ns


async def handle_client(
    websocket,
    input_dev: Optional[InputBackend],
    volume_dev: VolumeBackend,
    auth_token: str,
    require_auth: bool,
    connected_clients: dict,
    logger,
):
    client_addr = websocket.remote_address
    logger.info("Client connected: %s", client_addr)
    client_id = f"{client_addr[0]}:{client_addr[1]}"
    connected_clients[client_id] = time.time()

    authenticated = not require_auth

    try:
        async for raw_message in websocket:
            if isinstance(raw_message, bytes):
                if len(raw_message) >= 9 and raw_message[0:1] == b'm':
                    try:
                        dx = int.from_bytes(raw_message[1:5], 'big', signed=True)
                        dy = int.from_bytes(raw_message[5:9], 'big', signed=True)
                        if input_dev and authenticated:
                            input_dev.mouse_move(dx, dy)
                    except Exception:
                        pass
                    continue
                try:
                    raw_message = raw_message.decode("utf-8")
                except UnicodeDecodeError:
                    continue

            data = decode_message(raw_message)
            if data is None:
                continue

            msg_type = data.get("t", "")

            if msg_type == MSG_AUTH and require_auth:
                client_token = data.get("tk", "")
                if client_token == auth_token:
                    authenticated = True
                    await websocket.send(json.dumps({"t": "ok", "v": PROTOCOL_VERSION}))
                    logger.info("Client authenticated: %s", client_addr)
                else:
                    await websocket.send(json.dumps({"t": "err", "msg": "Invalid token"}))
                    logger.warning("Authentication failed for %s", client_addr)
                    return
                continue

            if not authenticated:
                await websocket.send(json.dumps({"t": "err", "msg": "Authentication required"}))
                continue

            if msg_type == MSG_PING:
                await websocket.send(json.dumps({"t": MSG_PONG, "ts": int(time.time() * 1000)}))
                connected_clients[client_id] = time.time()
                continue

            connected_clients[client_id] = time.time()

            if input_dev is None and msg_type not in (MSG_VOLUME_GET, MSG_VOLUME_SET, MSG_VOLUME_MUTE, MSG_PING):
                continue

            try:
                if msg_type == MSG_MOUSE_MOVE:
                    input_dev.mouse_move(data.get("x", 0), data.get("y", 0))

                elif msg_type == MSG_MOUSE_DOWN:
                    input_dev.mouse_button(data.get("b", "left"), "down")

                elif msg_type == MSG_MOUSE_UP:
                    input_dev.mouse_button(data.get("b", "left"), "up")

                elif msg_type == MSG_MOUSE_SCROLL:
                    input_dev.mouse_scroll(data.get("x", 0), data.get("y", 0))

                elif msg_type == MSG_KEY_DOWN:
                    name = data.get("c", "")
                    resolve_key, needs_shift = get_key_resolver()
                    if needs_shift(name):
                        input_dev.key("KEY_LEFTSHIFT", "down")
                    input_dev.key(name, "down")
                    if needs_shift(name):
                        input_dev.key("KEY_LEFTSHIFT", "up")

                elif msg_type == MSG_KEY_UP:
                    input_dev.key(data.get("c", ""), "up")

                elif msg_type == MSG_KEY_TAP:
                    name = data.get("c", "")
                    resolve_key, needs_shift = get_key_resolver()
                    shift = needs_shift(name)
                    if shift:
                        input_dev.key("KEY_LEFTSHIFT", "down")
                    input_dev.key(name, "down")
                    input_dev.key(name, "up")
                    if shift:
                        input_dev.key("KEY_LEFTSHIFT", "up")

                elif msg_type == MSG_TYPE_TEXT:
                    input_dev.type_text(data.get("tx", ""))

                elif msg_type == MSG_VOLUME_GET:
                    vol = volume_dev.get_volume()
                    await websocket.send(json.dumps({
                        "t": "vs", "f": "vg", "v": vol["volume"],
                        "m": vol["muted"], "v2": PROTOCOL_VERSION,
                    }))

                elif msg_type == MSG_VOLUME_SET:
                    volume_dev.set_volume(data.get("v", 50))
                    vol = volume_dev.get_volume()
                    await websocket.send(json.dumps({
                        "t": "vs", "f": "vs", "v": vol["volume"],
                        "m": vol["muted"], "v2": PROTOCOL_VERSION,
                    }))

                elif msg_type == MSG_VOLUME_MUTE:
                    muted = volume_dev.toggle_mute()
                    vol = volume_dev.get_volume()
                    await websocket.send(json.dumps({
                        "t": "vs", "f": "vm", "v": vol["volume"],
                        "m": muted, "v2": PROTOCOL_VERSION,
                    }))

            except Exception as e:
                logger.error("Error processing message type=%s: %s", msg_type, e)

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.pop(client_id, None)
        logger.info("Client disconnected: %s", client_addr)


async def cleanup_stale_clients(connected_clients: dict, timeout: float = 30.0):
    while True:
        await asyncio.sleep(10)
        now = time.time()
        stale = [cid for cid, ts in connected_clients.items() if now - ts > timeout]
        for cid in stale:
            connected_clients.pop(cid, None)


async def run_server(
    port: int,
    input_dev: Optional[InputBackend],
    volume_dev: VolumeBackend,
    auth_token: str,
    require_auth: bool,
    qr_backend,
    local_ip: str,
    logger,
):
    url = f"ws://{local_ip}:{port}"
    if require_auth:
        token_url = f"ws://{local_ip}:{port}?token={auth_token}"
    else:
        token_url = url

    logger.info("=" * 50)
    logger.info("  PcRemote Server v%s", VERSION)
    logger.info("=" * 50)
    logger.info("  Listening on: %s", url)
    if require_auth:
        logger.info("  Auth token: %s", auth_token)
    logger.info("  Protocol version: %d", PROTOCOL_VERSION)
    logger.info("  OS: %s", "Windows" if os.name == 'nt' else "Linux")
    logger.info("=" * 50)

    qr_backend.display(token_url)

    connected_clients: dict = {}

    asyncio.create_task(cleanup_stale_clients(connected_clients))

    async def handler(ws):
        await handle_client(ws, input_dev, volume_dev, auth_token, require_auth, connected_clients, logger)

    stop = asyncio.Future()

    async with serve(handler, "0.0.0.0", port, ping_interval=20, ping_timeout=10):
        logger.info("Server running. Press Ctrl+C to stop.")
        try:
            await stop
        except asyncio.CancelledError:
            pass


def main():
    if os.name == 'nt':
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="PC Remote companion server")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket port (default: 8765)")
    parser.add_argument("--password", type=str, default=None,
                        help="Require authentication token for connections")
    parser.add_argument("--no-input", action="store_true",
                        help="Run without input simulation (testing mode)")
    parser.add_argument("--no-diagnostics", action="store_true",
                        help="Skip startup diagnostics")
    parser.add_argument("--no-qr", action="store_true",
                        help="Don't display QR code")
    parser.add_argument("--tray", action="store_true",
                        help="Start minimized in system tray (Windows only)")
    parser.add_argument("--keep-mouse-accel", action="store_true",
                        help="Keep Windows mouse acceleration enabled")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")
    parser.add_argument("--version", action="version",
                        version=f"PcRemote v{VERSION} (protocol v{PROTOCOL_VERSION})")
    args = parser.parse_args()

    log_level = "DEBUG" if args.debug else "INFO"
    import logging
    logger = setup_logging(getattr(logging, log_level))
    logger.info("PcRemote v%s starting...", VERSION)

    if not args.no_diagnostics:
        logger.info("Running startup diagnostics...")
        results = run_diagnostics(args.port, logger)
        if results.get("firewall") == "blocked":
            logger.info("Attempting to auto-fix firewall...")
            auto_fix_firewall(args.port, logger)

    ip = get_local_ip()

    config = load_config()
    require_auth = args.password is not None
    auth_token = args.password or get_or_create_token(config)

    if args.no_input:
        input_dev = None
        logger.info("TEST MODE - no input simulation")
    else:
        try:
            logger.info("Initialising input devices...")
            input_dev = create_input_backend(
                disable_mouse_accel=not args.keep_mouse_accel
            )
            logger.info("Input devices ready.")
        except PermissionError:
            logger.error("Permission denied accessing input device.")
            if os.name != 'nt':
                logger.error("  Run: sudo modprobe uinput")
                logger.error("  Then: sudo usermod -aG input $USER")
            sys.exit(1)
        except Exception as e:
            logger.error("Failed to initialise input: %s", e)
            sys.exit(1)

    volume_dev = create_volume_backend()
    qr_backend = QrBackends.create()

    try:
        asyncio.run(run_server(
            args.port, input_dev, volume_dev, auth_token,
            require_auth, qr_backend, ip, logger,
        ))
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        if input_dev:
            input_dev.close()
        logger.info("Server stopped.")


if __name__ == "__main__":
    main()
