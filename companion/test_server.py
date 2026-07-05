#!/usr/bin/env python3
"""Automated test client for PcRemote v2 server.

Connects via WebSocket, sends a sequence of input commands,
verifies responses, and reports results.

Usage:
    python3 test_server.py [--port PORT] [--host HOST]
"""

import argparse
import asyncio
import json
import sys
import time
import websockets

PASS = 0
FAIL = 0


def ok(msg):
    global PASS
    PASS += 1
    print(f"  [PASS] {msg}")


def fail(msg):
    global FAIL
    FAIL += 1
    print(f"  [FAIL] {msg}")


async def test_server(host="127.0.0.1", port=8765):
    global PASS, FAIL
    PASS = 0
    FAIL = 0
    url = f"ws://{host}:{port}"

    print(f"Connecting to {url}...")
    try:
        async with websockets.connect(url) as ws:
            ok("Connected")

            print("\n--- Protocol tests ---")

            pong_future = await ws.ping()
            try:
                await asyncio.wait_for(pong_future, timeout=5)
                ok("WebSocket ping/pong")
            except TimeoutError:
                fail("WebSocket ping/pong (timeout)")

            await ws.send(json.dumps({"t": "pi"}))
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=3)
                data = json.loads(resp)
                if data.get("t") == "po":
                    ok("App-level ping/pong")
                else:
                    fail(f"App-level ping: unexpected response {data}")
            except TimeoutError:
                fail("App-level ping (timeout)")

            print("\n--- Mouse tests ---")

            msgs = [
                {"t": "m", "x": 10.0, "y": 0.0},
                {"t": "m", "x": 0.0, "y": 10.0},
                {"t": "m", "x": -10.0, "y": -10.0},
                {"t": "md", "b": "left"},
                {"t": "mu", "b": "left"},
                {"t": "md", "b": "right"},
                {"t": "mu", "b": "right"},
                {"t": "md", "b": "middle"},
                {"t": "mu", "b": "middle"},
                {"t": "s", "x": 0, "y": 3},
                {"t": "s", "x": 0, "y": -3},
                {"t": "s", "x": 3, "y": 0},
            ]
            for msg in msgs:
                await ws.send(json.dumps(msg))
            await asyncio.sleep(0.5)
            ok("Mouse events sent (12 messages)")

            print("\n--- Keyboard tests ---")

            for ch in "abcdefghijklmnopqrstuvwxyz":
                await ws.send(json.dumps({"t": "kt", "c": ch}))
            await ws.send(json.dumps({"t": "kt", "c": "KEY_SPACE"}))
            await ws.send(json.dumps({"t": "kt", "c": "KEY_ENTER"}))

            await ws.send(json.dumps({"t": "kd", "c": "KEY_LEFTSHIFT"}))
            await ws.send(json.dumps({"t": "kt", "c": "A"}))
            await ws.send(json.dumps({"t": "ku", "c": "KEY_LEFTSHIFT"}))

            await ws.send(json.dumps({"t": "kd", "c": "KEY_LEFTCTRL"}))
            await ws.send(json.dumps({"t": "kt", "c": "c"}))
            await ws.send(json.dumps({"t": "ku", "c": "KEY_LEFTCTRL"}))

            for fx in range(1, 13):
                await ws.send(json.dumps({"t": "kt", "c": f"KEY_F{fx}"}))

            for k in ["KEY_TAB", "KEY_ESC", "KEY_BACKSPACE", "KEY_DELETE",
                       "KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT",
                       "KEY_HOME", "KEY_END", "KEY_PAGEUP", "KEY_PAGEDOWN"]:
                await ws.send(json.dumps({"t": "kt", "c": k}))

            await asyncio.sleep(0.5)
            ok("Key events sent (all keys)")

            print("\n--- Italian layout tests ---")

            it_chars = "èéòçàùìÈÉÒÇÀÙÌ€@#[]{}~"
            for ch in it_chars:
                await ws.send(json.dumps({"t": "kt", "c": ch}))
            await asyncio.sleep(0.5)
            ok(f"Italian layout chars sent ({len(it_chars)} chars)")

            print("\n--- Text/Unicode tests ---")

            await ws.send(json.dumps({"t": "tx", "tx": "Ciao mondo! 😀🔥"}))
            await asyncio.sleep(0.5)
            ok("Text with emoji sent")

            print("\n--- Volume tests ---")

            await ws.send(json.dumps({"t": "vg"}))
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=3)
                data = json.loads(resp)
                if data.get("t") == "vs":
                    ok(f"Volume get: {data.get('v', '?')}% (muted={data.get('m', '?')})")
                else:
                    fail(f"Volume get: unexpected response {data}")
            except TimeoutError:
                fail("Volume get (timeout)")

            await ws.send(json.dumps({"t": "vs", "v": 42}))
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=3)
                data = json.loads(resp)
                if data.get("t") == "vs" and data.get("f") == "vs":
                    ok(f"Volume set to 42: got {data.get('v', '?')}")
                else:
                    fail(f"Volume set: unexpected response {data}")
            except TimeoutError:
                fail("Volume set (timeout)")

            await ws.send(json.dumps({"t": "vm"}))
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=3)
                data = json.loads(resp)
                if data.get("t") == "vs" and data.get("f") == "vm":
                    ok(f"Volume mute toggle: muted={data.get('m', '?')}")
                else:
                    fail(f"Volume mute: unexpected response {data}")
            except TimeoutError:
                fail("Volume mute (timeout)")

            print("\n--- Stress test (rapid fire) ---")
            t0 = time.monotonic()
            for i in range(200):
                await ws.send(json.dumps({"t": "m", "x": 1.0, "y": 0.0}))
            elapsed = (time.monotonic() - t0) * 1000
            ok(f"200 mouse moves in {elapsed:.0f}ms ({200000/elapsed:.0f} msg/s)")

            print("\n--- Latency test ---")
            latencies = []
            for _ in range(10):
                t0 = time.monotonic()
                pong_future = await ws.ping()
                await pong_future
                latencies.append((time.monotonic() - t0) * 1000)
            avg_lat = sum(latencies) / len(latencies)
            ok(f"Avg ping latency: {avg_lat:.1f}ms (min={min(latencies):.1f} max={max(latencies):.1f})")

    except OSError as e:
        fail(f"Connection failed: {e}")
        return

    print(f"\n{'='*40}")
    print(f"Results: {PASS} passed, {FAIL} failed")
    print(f"{'='*40}")
    return FAIL == 0


def main():
    parser = argparse.ArgumentParser(description="Test PcRemote v2 server")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    success = asyncio.run(test_server(args.host, args.port))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
