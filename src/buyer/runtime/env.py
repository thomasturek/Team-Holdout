"""Settings from `.env`: the repo root first, then `starter-kit/.env`. Real environment variables win.

A relative ARENA_DATA is resolved against the folder of the `.env` file that sets it, so
`ARENA_DATA=../data` in `starter-kit/.env` and `ARENA_DATA=data` in the root `.env` both find the
package whether you run from the repo root or from `starter-kit/`.
"""

import os
from pathlib import Path

from arena_kit.cli import load_env

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "runs"
ENV_FILES = (ROOT / ".env", ROOT / "starter-kit" / ".env")
PATH_KEYS = ("ARENA_DATA",)


def load(files=ENV_FILES):
    for path in files:
        before = {k: os.environ.get(k) for k in PATH_KEYS}
        load_env(path)
        for key in PATH_KEYS:
            value = os.environ.get(key)
            if before[key] is None and value and not Path(value).is_absolute():
                os.environ[key] = str((Path(path).parent / value).resolve())
