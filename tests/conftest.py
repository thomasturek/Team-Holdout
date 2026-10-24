import secrets
import socket
import threading
import time

import pytest
from arena_kit import ArenaClient


class Clock:
    """A clock the tests move by hand, so the 60-second rule is testable without waiting."""

    def __init__(self):
        self.now = 1_000_000.0

    def __call__(self):
        return self.now


class SlowArena:
    """ASGI wrapper around arena-sim that behaves like a hosted arena under load: a supplier's reply
    takes `reply_s[supplier]` seconds, and with `serial` the arena handles one call per session at a
    time (the kit: "a call may wait for another call on the same session first")."""

    def __init__(self, app, reply_s, serial):
        import asyncio
        import collections
        import re

        self.app, self.reply_s, self.serial = app, reply_s, serial
        self.locks = collections.defaultdict(asyncio.Lock)
        self.path = re.compile(r"^/v1/sessions/([^/]+)/(?:threads/([^/]+)/messages)?")

    async def __call__(self, scope, receive, send):
        import asyncio
        import contextlib

        m = self.path.match(scope.get("path", "")) if scope["type"] == "http" else None
        if not m:
            return await self.app(scope, receive, send)
        lock = self.locks[m.group(1)] if self.serial else contextlib.nullcontext()
        async with lock:
            if scope["method"] == "POST" and m.group(2):
                await asyncio.sleep(self.reply_s.get(m.group(2).replace("%3A", ":"), 0))
            await self.app(scope, receive, send)


def serve(app):
    import uvicorn

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.01)
    return server, thread, f"http://127.0.0.1:{port}"


@pytest.fixture
def slow_sim():
    """A factory: slow_sim(reply_s={supplier: seconds}, serial=True) -> client of a fresh SlowArena."""
    from arena_kit.sim import Sim, create_app, load_cases

    servers = []

    def make(reply_s, serial=True):
        state = Sim(load_cases(), clock=Clock())
        server, thread, url = serve(SlowArena(create_app(state), reply_s, serial))
        servers.append((server, thread))
        key = ArenaClient(url).register(f"test-{secrets.token_hex(3)}", "sim")["api_key"]
        return ArenaClient(url, key, rate=1000)

    yield make
    for server, thread in servers:
        server.should_exit = True
        thread.join()


@pytest.fixture
def sim():
    """arena-sim on a free local port: (client, Sim, Clock) - a fresh team key, no rate pacing."""
    import uvicorn
    from arena_kit.sim import Sim, create_app, load_cases

    clock = Clock()
    state = Sim(load_cases(), clock=clock)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(state), port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.01)
    url = f"http://127.0.0.1:{port}"
    key = ArenaClient(url).register(f"test-{secrets.token_hex(3)}", "sim")["api_key"]
    yield ArenaClient(url, key, rate=1000), state, clock
    server.should_exit = True
    thread.join()
