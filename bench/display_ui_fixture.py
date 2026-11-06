"""Serve synthetic display metadata for browser UI checks; never captures a desktop.

Bundle web/src into a directory with esbuild, then pass --assets DIRECTORY.
Scenarios: /, /?scenario=readonly, /?scenario=single, /?scenario=failure.
"""
import argparse
import asyncio
from http import HTTPStatus
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from websockets.asyncio.server import serve
from websockets.datastructures import Headers
from websockets.http11 import Response

root = Path(__file__).resolve().parents[1]
clients = set()
selected = 10
generation = 0
commands = []


def hello(scenario):
    available = [
        {"id": 10, "name": "Display 1", "width": 1280, "height": 720, "main": True},
        {"id": 20, "name": "Display 2", "width": 1280, "height": 720, "main": False},
    ]
    if scenario == "single":
        available = available[:1]
    return json.dumps({
        "t": "hello", "w": 1280, "h": 720, "os": "macos", "audio": False,
        "readOnly": scenario == "readonly",
        "displays": {"available": available, "selected": selected if scenario != "single" else 10,
                     "generation": generation, "switching": False},
    })


async def socket_handler(ws):
    global selected, generation
    scenario = parse_qs(urlparse(ws.request.path).query).get("scenario", [""])[0]
    clients.add((ws, scenario))
    try:
        await ws.send(hello(scenario))
        async for command in ws:
            if not isinstance(command, str):
                continue
            commands.append(command)
            if command.startswith("ds,") and scenario != "readonly":
                if scenario == "failure":
                    await ws.send(json.dumps({"t": "display-error", "message": "Test display is unavailable."}))
                    continue
                for client, _ in list(clients):
                    await client.send('{"t":"display-switching"}')
                await asyncio.sleep(0.2)
                selected = int(command.split(",")[1])
                generation += 1
                for client, mode in list(clients):
                    await client.send(hello(mode))
    finally:
        clients.discard((ws, scenario))


async def main(assets, port):
    def http(_connection, request):
        if request.headers.get("Upgrade", "").lower() == "websocket":
            return None
        path = urlparse(request.path).path
        status = 200
        content_type = "application/javascript"
        if path == "/":
            body = (root / "web/index.html").read_bytes().replace(b"{{title}}", b"Voxl synthetic display UI")
            content_type = "text/html; charset=utf-8"
        elif path in ["/client.js", "/worker.js", "/audio.js", "/mic.js"]:
            body = (assets / path[1:]).read_bytes()
        elif path in ["/favicon.ico", "/inter.woff2"]:
            body = (root / "web" / path[1:]).read_bytes()
            content_type = "image/x-icon" if path.endswith(".ico") else "font/woff2"
        elif path == "/fixture-state":
            body = json.dumps({"selected": selected, "generation": generation, "commands": commands}).encode()
            content_type = "application/json"
        else:
            body = b"not found"; status = 404
        return Response(status, HTTPStatus(status).phrase, Headers({
            "Content-Type": content_type, "Content-Length": str(len(body)), "Cache-Control": "no-store",
        }), body)

    async with serve(socket_handler, "127.0.0.1", port, process_request=http):
        print(f"Synthetic UI fixture: http://127.0.0.1:{port}/", flush=True)
        await asyncio.Future()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--port", type=int, default=16902)
    args = parser.parse_args()
    asyncio.run(main(args.assets, args.port))
