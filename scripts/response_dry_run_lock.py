"""Advisory locks for response dry-run fixture files."""

from __future__ import annotations

import fcntl
import hashlib
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

GLOBAL_FIXTURE_STATE_KEY = "__enterprise_response_fixture_state__"
_PROCESS_GLOBAL_LOCK = threading.RLock()
_GLOBAL_LOCK_DEPTH = 0
_GLOBAL_LOCK_FILE: TextIO | None = None


@contextmanager
def response_dry_run_lock(repo_root: Path, response_rel: str | Path) -> Iterator[None]:
    """Serialize temporary writes to a normalized-response fixture path."""

    lock_dir = repo_root / "var" / "locks" / "response-dry-runs"
    lock_dir.mkdir(parents=True, exist_ok=True)
    response_key = Path(response_rel).as_posix()
    with _global_fixture_state_lock(lock_dir):
        if response_key == GLOBAL_FIXTURE_STATE_KEY:
            yield
            return
        lock_file = (lock_dir / _lock_name(response_key)).open("a+", encoding="utf-8")
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()


def _lock_name(response_key: str) -> str:
    return hashlib.sha256(response_key.encode("utf-8")).hexdigest() + ".lock"


@contextmanager
def _global_fixture_state_lock(lock_dir: Path) -> Iterator[None]:
    global _GLOBAL_LOCK_DEPTH, _GLOBAL_LOCK_FILE

    _PROCESS_GLOBAL_LOCK.acquire()
    try:
        if _GLOBAL_LOCK_DEPTH == 0:
            _GLOBAL_LOCK_FILE = (lock_dir / _lock_name(GLOBAL_FIXTURE_STATE_KEY)).open(
                "a+", encoding="utf-8"
            )
            fcntl.flock(_GLOBAL_LOCK_FILE.fileno(), fcntl.LOCK_EX)
        _GLOBAL_LOCK_DEPTH += 1
        try:
            yield
        finally:
            _GLOBAL_LOCK_DEPTH -= 1
            if _GLOBAL_LOCK_DEPTH == 0:
                assert _GLOBAL_LOCK_FILE is not None
                fcntl.flock(_GLOBAL_LOCK_FILE.fileno(), fcntl.LOCK_UN)
                _GLOBAL_LOCK_FILE.close()
                _GLOBAL_LOCK_FILE = None
    finally:
        _PROCESS_GLOBAL_LOCK.release()
