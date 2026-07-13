"""SQLite persistence for runs and their event streams, so build history
survives app restarts. Stored at <workspace>/devfoundry.db."""
import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any

from app.config import get_settings
from app.models.schemas import PipelineEvent, RunState

log = logging.getLogger(__name__)

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def _db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        path = get_settings().devfoundry_workspace / "devfoundry.db"
        _conn = sqlite3.connect(str(path), check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                idea TEXT NOT NULL,
                stage TEXT NOT NULL,
                error TEXT,
                artifacts TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                kind TEXT NOT NULL,
                message TEXT NOT NULL,
                payload TEXT NOT NULL DEFAULT '{}',
                ts TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id, id);
            """
        )
        _conn.commit()
    return _conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_run(state: RunState) -> None:
    with _lock:
        db = _db()
        exists = db.execute("SELECT 1 FROM runs WHERE run_id=?", (state.run_id,)).fetchone()
        if exists:
            db.execute(
                "UPDATE runs SET stage=?, error=?, artifacts=?, updated_at=? WHERE run_id=?",
                (state.stage.value, state.error, json.dumps(state.artifacts, default=str), _now(), state.run_id),
            )
        else:
            db.execute(
                "INSERT INTO runs (run_id, idea, stage, error, artifacts, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (state.run_id, state.idea, state.stage.value, state.error,
                 json.dumps(state.artifacts, default=str), _now(), _now()),
            )
        db.commit()


def save_event(event: PipelineEvent) -> None:
    with _lock:
        db = _db()
        db.execute(
            "INSERT INTO events (run_id, stage, kind, message, payload, ts) VALUES (?,?,?,?,?,?)",
            (event.run_id, event.stage.value, event.kind, event.message,
             json.dumps(event.payload, default=str), event.ts.isoformat()),
        )
        db.commit()


def list_runs(limit: int = 200) -> list[dict[str, Any]]:
    with _lock:
        rows = _db().execute(
            "SELECT run_id, idea, stage, error, artifacts, created_at, updated_at "
            "FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [{
        "run_id": r[0], "idea": r[1], "stage": r[2], "error": r[3],
        "artifacts": json.loads(r[4]), "created_at": r[5], "updated_at": r[6],
    } for r in rows]


def get_run(run_id: str) -> dict[str, Any] | None:
    with _lock:
        r = _db().execute(
            "SELECT run_id, idea, stage, error, artifacts, created_at, updated_at "
            "FROM runs WHERE run_id=?", (run_id,)).fetchone()
    if not r:
        return None
    return {"run_id": r[0], "idea": r[1], "stage": r[2], "error": r[3],
            "artifacts": json.loads(r[4]), "created_at": r[5], "updated_at": r[6]}


def get_events(run_id: str) -> list[dict[str, Any]]:
    with _lock:
        rows = _db().execute(
            "SELECT run_id, stage, kind, message, payload, ts FROM events "
            "WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
    return [{"run_id": r[0], "stage": r[1], "kind": r[2], "message": r[3],
             "payload": json.loads(r[4]), "ts": r[5]} for r in rows]


def delete_run(run_id: str) -> bool:
    with _lock:
        db = _db()
        cur = db.execute("DELETE FROM runs WHERE run_id=?", (run_id,))
        db.execute("DELETE FROM events WHERE run_id=?", (run_id,))
        db.commit()
        return cur.rowcount > 0
