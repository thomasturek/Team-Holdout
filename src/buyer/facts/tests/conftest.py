import pytest


@pytest.fixture(autouse=True)
def _real_data(monkeypatch):
    """Other suites write ARENA_DATA into os.environ (load_env); the facts tests read the repo's data/."""
    monkeypatch.delenv("ARENA_DATA", raising=False)
    monkeypatch.delenv("ARENA_RELEASE", raising=False)
