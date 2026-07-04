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
import threading
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

_profile_stats: dict = {}
_server_control: dict = {}


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def create_input_backend() -> InputBackend:
    if os.name == 'nt':
        from pcremote.backends.windows import WindowsSendInputBackend
        return WindowsSendInputBackend()
    else:
        from pcremote.backends.linux import LinuxUinputBackend


def create_volume_backend() -> VolumeBackend:
    if os.name == 'nt':
        from pcremote.backends.windows import WindowsVolumeBackend
        return WindowsVolumeBackend()
    else:
        from pcremote.backends.linux import LinuxPactlBackend


def get_key_resolver():
    if os.name == 'nt':
        from pcremote.backends.windows import resolve_key as rk, needs_shift as ns
        return rk, ns
    else:
        from pcremote.backends.linux import resolve_key as rk, needs_shift as ns
        return rk, ns


def _profile_msg(msg_type: str, start_time: float, logger):
    elapsed = (time.monotonic() - start_time) * 1000
    if msg_type not in _profile_stats:
        _profile_stats[msg_type] = {"total": 0.0, "count": 0, "max": 0.0}
    s = _profile_stats[msg_type]
    s["total"] += elapsed
    s["count"] += 1
    if elapsed > s["max"]:
        s["max"] = elapsed
    if s["count"] % 500 == 0:
        logger.debug(
            "msg=%s avg=%.2fms max=%.2fms count=%d",
            msg_type, s["total"] / s["count"], s["max"], s["count"],
        )


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
            msg_start = time.monotonic()

            if input_dev is None and msg_type not in (MSG_VOLUME_GET, MSG_VOLUME_SET, MSG_VOLUME_MUTE, MSG_PING):
                continue

            try:
                if msg_type == MSG_MOUSE_MOVE:
                    input_dev.mouse_move(data.get("x", 0), data.get("y", 0))
                    _profile_msg("m", msg_start, logger)
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


class ServerInstance:
    def __init__(self, port, input_dev, volume_dev, auth_token, require_auth,
                 qr_backend, local_ip, logger):
        self.port = port
        self.input_dev = input_dev
        self.volume_dev = volume_dev
        self.auth_token = auth_token
        self.require_auth = require_auth
        self.qr_backend = qr_backend
        self.local_ip = local_ip
        self.logger = logger
        self._task = None
        self._stop_event = None

    async def _run(self):
        url = f"ws://{self.local_ip}:{self.port}"
        token_url = url
        if self.require_auth:
            token_url = f"ws://{self.local_ip}:{self.port}?token={self.auth_token}"

        self.logger.info("=" * 50)
        self.logger.info("  PcRemote Server v%s", VERSION)
        self.logger.info("=" * 50)
        self.logger.info("  Listening on: %s", url)
        if self.require_auth:
            self.logger.info("  Auth token: %s", self.auth_token)
        self.logger.info("  Protocol version: %d", PROTOCOL_VERSION)
        self.logger.info("  OS: %s", "Windows" if os.name == 'nt' else "Linux")
        self.logger.info("=" * 50)

        if self.input_dev and hasattr(self.input_dev, 'start_ticker'):
            self.input_dev.start_ticker(asyncio.get_running_loop())

        connected_clients: dict = {}
        asyncio.create_task(cleanup_stale_clients(connected_clients))

        async def handler(ws):
            await handle_client(ws, self.input_dev, self.volume_dev,
                                self.auth_token, self.require_auth,
                                connected_clients, self.logger)

        self._stop_event = asyncio.Event()
        async with serve(handler, "0.0.0.0", self.port, ping_interval=20, ping_timeout=10):
            self.logger.info("Server running.")
            await self._stop_event.wait()

    def start(self, loop):
        self._task = loop.create_task(self._run())

    def stop(self):
        if self._stop_event:
            self._stop_event.set()
        if self.input_dev:
            self.input_dev.close()


class AppController:
    def __init__(self, args, logger):
        self.args = args
        self.logger = logger
        self.config = load_config()
        self.require_auth = args.password is not None
        self.auth_token = args.password or get_or_create_token(self.config)
        self.ip = get_local_ip()
        self.server = None
        self.input_dev = None
        self.volume_dev = None
        self.qr_backend = None
        self._loop = None

    def _create_backends(self):
        if self.args.no_input:
            self.input_dev = None
        else:
            self.input_dev = create_input_backend()
        self.volume_dev = create_volume_backend()
        self.qr_backend = QrBackends.create()

    def _destroy_backends(self):
        if self.input_dev:
            try:
                self.input_dev.close()
            except Exception:
                pass
            self.input_dev = None

    def start_server(self):
        if self.server is not None:
            return
        self._create_backends()
        self.server = ServerInstance(
            self.args.port, self.input_dev, self.volume_dev,
            self.auth_token, self.require_auth,
            self.qr_backend, self.ip, self.logger,
        )
        self.server.start(self._loop)
        self.logger.info("Server started on %s:%d", self.ip, self.args.port)

    def stop_server(self):
        if self.server is None:
            return
        self.server.stop()
        self.server = None
        self._destroy_backends()
        self.logger.info("Server stopped.")

    def get_connection_url(self) -> str:
        url = f"ws://{self.ip}:{self.args.port}"
        if self.require_auth:
            url = f"ws://{self.ip}:{self.args.port}?token={self.auth_token}"
        return url

    def close_qr_window(self):
        if self.qr_backend:
            self.qr_backend.close_qr()

    def run(self):
        if os.name == 'nt' and not self.args.console:
            self._run_tray_mode()
        else:
            self._run_console_mode()

    def _run_console_mode(self):
        if not self.args.no_diagnostics:
            self.logger.info("Running startup diagnostics...")
            results = run_diagnostics(self.args.port, self.logger)
            if results.get("firewall") == "blocked":
                self.logger.info("Attempting to auto-fix firewall...")
                auto_fix_firewall(self.args.port, self.logger)

        if not self.args.no_input:
            self.logger.info("Initialising input devices...")
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self.start_server()
        try:
            self._loop.run_forever()
        except KeyboardInterrupt:
            self.logger.info("Shutting down...")
        finally:
            self.stop_server()
            self._loop.close()
            self.logger.info("Server stopped.")

    def _run_tray_mode(self):
        from pcremote.tray import run_tray

        self.logger.info("Running startup diagnostics...")
        results = run_diagnostics(self.args.port, self.logger)
        if results.get("firewall") == "blocked":
            self.logger.info("Attempting to auto-fix firewall...")
            auto_fix_firewall(self.args.port, self.logger)

        self._loop = asyncio.new_event_loop()

        def _run_loop():
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()

        loop_thread = threading.Thread(target=_run_loop, daemon=True)
        loop_thread.start()

        def on_init():
            self._loop.call_soon_threadsafe(self.start_server)

        def on_start():
            self._loop.call_soon_threadsafe(self.start_server)

        def on_stop():
            self._loop.call_soon_threadsafe(self.stop_server)

        def on_quit():
            self._loop.call_soon_threadsafe(self._loop.stop)
            loop_thread.join(timeout=2)
            sys.exit(0)

        try:
            run_tray(on_stop, on_start, on_quit,
                     on_init=on_init,
                     get_connection_url=self.get_connection_url)
        except KeyboardInterrupt:
            self.logger.info("Shutting down...")
        finally:
            self.stop_server()
            self._loop.call_soon_threadsafe(self._loop.stop)


def main():
    if os.name == 'nt':
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="PC Remote companion server")
    parser.add_argument("--port", type=int, default=8765,
                        help="WebSocket port (default: 8765)")
    parser.add_argument("--password", type=str, default=None,
                        help="Require authentication token for connections")
    parser.add_argument("--no-input", action="store_true",
                        help="Run without input simulation (testing mode)")
    parser.add_argument("--no-diagnostics", action="store_true",
                        help="Skip startup diagnostics")
    parser.add_argument("--no-qr", action="store_true",
                        help="Don't display QR code")
    parser.add_argument("--console", action="store_true",
                        help="Run in console mode (skip system tray on Windows)")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")
    parser.add_argument("--version", action="version",
                        version=f"PcRemote v{VERSION} (protocol v{PROTOCOL_VERSION})")
    args = parser.parse_args()

    log_level = "DEBUG" if args.debug else "INFO"
    import logging
    logger = setup_logging(getattr(logging, log_level))
    logger.info("PcRemote v%s starting...", VERSION)

    app = AppController(args, logger)
    app.run()


if __name__ == "__main__":
    main()
