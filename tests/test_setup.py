"""The root project: the kit imports from the repo root and `.env` loading follows our rules."""

import os
from pathlib import Path

from buyer.runtime import env


def test_the_kit_imports_from_the_root():
    import arena_kit
    from arena_kit.cost import total_cost  # noqa: F401

    assert Path(arena_kit.__file__).resolve().is_relative_to(env.ROOT / "starter-kit")


def test_env_files_load_in_order_and_resolve_the_data_path(tmp_path, monkeypatch):
    root, kit = tmp_path / "root", tmp_path / "root" / "starter-kit"
    kit.mkdir(parents=True)
    (root / ".env").write_text("ARENA_URL=http://root\n")
    (kit / ".env").write_text("ARENA_URL=http://kit\nARENA_DATA=../data\nARENA_API_KEY=k\n")
    for key in ("ARENA_URL", "ARENA_DATA", "ARENA_API_KEY"):
        monkeypatch.setenv(key, "")  # recorded, so the teardown also removes what env.load sets below
        monkeypatch.delenv(key)
    env.load((root / ".env", kit / ".env"))
    assert os.environ["ARENA_URL"] == "http://root"  # the root file wins over starter-kit/.env
    assert os.environ["ARENA_API_KEY"] == "k"  # what the root file leaves out comes from the kit's
    assert Path(os.environ["ARENA_DATA"]) == (root / "data").resolve()


def test_real_environment_variables_win(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("ARENA_URL=http://file\nARENA_DATA=data\n")
    monkeypatch.setenv("ARENA_URL", "http://real")
    monkeypatch.setenv("ARENA_DATA", "elsewhere")
    env.load((tmp_path / ".env",))
    assert os.environ["ARENA_URL"] == "http://real"
    assert os.environ["ARENA_DATA"] == "elsewhere"


def test_secrets_and_logs_stay_out_of_git():
    ignored = (env.ROOT / ".gitignore").read_text().splitlines()
    assert ".env" in ignored and "runs/" in ignored
