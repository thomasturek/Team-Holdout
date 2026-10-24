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
