"""
PostgreSQL access layer — the single connection pool + row factory for Conwo.

This module replaces the per-store `sqlite3.connect(...)` helpers. Every store
(auth, conversations, traces) and every read tool (jira, configs) acquires its
connection from the one pool defined here, pointed at the `wis_conwo` database.

Why a custom Row factory (the load-bearing piece)
-------------------------------------------------
The codebase was written against `sqlite3.Row`, which is unusual: a single row
object supports BOTH positional and name indexing AND iterates as *values*:

    row[0]                       # by position
    row["col"]                   # by name
    dict(row)                    # via keys() + __getitem__
    dict(zip(cols, row))         # iterates row as VALUES
    a, b, c = row                # tuple-unpack -> VALUES

Neither psycopg's `dict_row` (name-only, iterates keys) nor `tuple_row`
(position-only) reproduces all of these. A single wrong choice silently
corrupts data — e.g. `dict(zip(cols, row))` under `dict_row` zips column names
against column names. So we ship a faithful `sqlite3.Row` clone (`Row`) and use
it as the pool-wide `row_factory`. With it, every existing call site keeps
working unchanged.

Transaction semantics
----------------------
Connections are autocommit by default (mirrors the old `isolation_level=None`
stores). Callers that need a multi-statement atomic block use
`with conn.transaction():` explicitly (e.g. trace_store.end_session).
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence

import psycopg
from psycopg_pool import ConnectionPool

_log = logging.getLogger("uvicorn.error")

ROOT = Path(__file__).resolve().parent.parent
# Postgres DDL lives in migrations/postgres/. The legacy migrations/002_auth_store.sql
# is a SQLite reference copy and is intentionally NOT run by init_db().
MIGRATIONS_DIR = ROOT / "migrations" / "postgres"


# ── Faithful sqlite3.Row clone ──────────────────────────────────────────────
class Row:
    """A psycopg row object that behaves like ``sqlite3.Row``.

    Supports ``row[int]``, ``row[str]``, ``len(row)``, iteration over VALUES
    (so ``dict(zip(cols, row))`` and ``a, b, c = row`` work), and ``keys()``
    (so ``dict(row)`` works). On duplicate column names, the *first* wins —
    matching sqlite3.Row.
    """

    __slots__ = ("_cols", "_vals", "_map")

    def __init__(self, cols: Sequence[str], vals: Sequence[Any]) -> None:
        self._cols = tuple(cols)
        self._vals = tuple(vals)
        m: dict[str, int] = {}
        for i, c in enumerate(self._cols):
            m.setdefault(c, i)  # first occurrence wins, like sqlite3.Row
        self._map = m

    def keys(self) -> list[str]:
        return list(self._cols)

    def __getitem__(self, key: int | str | slice) -> Any:
        if isinstance(key, (int, slice)):
            return self._vals[key]
        try:
            return self._vals[self._map[key]]
        except KeyError:
            raise KeyError(key) from None

    def __iter__(self) -> Iterator[Any]:
        # Yields VALUES — critical for dict(zip(cols, row)) and tuple-unpack.
        return iter(self._vals)

    def __len__(self) -> int:
        return len(self._vals)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Row):
            return self._cols == other._cols and self._vals == other._vals
        return NotImplemented

    def __repr__(self) -> str:
        pairs = ", ".join(f"{c}={v!r}" for c, v in zip(self._cols, self._vals))
        return f"<Row {pairs}>"


def _row_factory(cursor: psycopg.Cursor) -> Any:
    """psycopg row_factory: (cursor) -> (values -> Row)."""
    desc = cursor.description or []
    cols = [d.name for d in desc]

    def make_row(values: Sequence[Any]) -> Row:
        return Row(cols, values)

    return make_row


# ── Pool config ─────────────────────────────────────────────────────────────
def _env(name: str, default: str | None = None) -> str:
    val = os.getenv(name, default if default is not None else "")
    return val.strip()


def _dsn() -> str:
    """Return the Postgres connection string.

    If DATABASE_URL is set (DevOps' platform convention — a single
    postgresql://user:pass@host:port/db?sslmode=require URI), use it verbatim;
    libpq/psycopg accept it directly. Otherwise build a libpq keyword string from
    the discrete CONWO_DB_* vars (local dev / explicit config). Secrets are read
    from the environment only — never logged or defaulted.
    """
    url = _env("DATABASE_URL")
    if url:
        return url

    host = _env("CONWO_DB_HOST", "localhost")
    port = _env("CONWO_DB_PORT", "5432")
    name = _env("CONWO_DB_NAME", "wis_conwo")
    user = _env("CONWO_DB_USER", "wis_conwo")
    password = _env("CONWO_DB_PASSWORD")
    sslmode = _env("CONWO_DB_SSLMODE", "disable")
    if not password:
        raise RuntimeError(
            "CONWO_DB_PASSWORD is not set. Configure the CONWO_DB_* vars in .env "
            "(local) or the deployment environment (prod) and restart."
        )
    return (
        f"host={host} port={port} dbname={name} user={user} "
        f"password={password} sslmode={sslmode}"
    )


def _schema() -> str:
    return _env("CONWO_DB_SCHEMA", "public")


def _configure(conn: psycopg.Connection) -> None:
    """Run once per physical pooled connection."""
    conn.autocommit = True
    conn.row_factory = _row_factory
    # Explicit search_path so unqualified table names always resolve.
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {_schema()}")


_pool: ConnectionPool | None = None


def init_pool() -> None:
    """Create and open the global pool. Idempotent. Raises on unreachable DB."""
    global _pool
    if _pool is not None:
        return
    min_size = int(_env("CONWO_DB_POOL_MIN", "1") or "1")
    max_size = int(_env("CONWO_DB_POOL_MAX", "10") or "10")
    pool = ConnectionPool(
        conninfo=_dsn(),
        min_size=min_size,
        max_size=max_size,
        configure=_configure,
        open=False,
        name="conwo",
    )
    pool.open()
    try:
        pool.wait(timeout=10.0)
    except Exception as exc:
        host, name = _env("CONWO_DB_HOST", "localhost"), _env("CONWO_DB_NAME", "wis_conwo")
        pool.close()
        raise RuntimeError(
            f"Could not connect to PostgreSQL at {host}/{name}: {exc}. "
            "Check CONWO_DB_* env vars and that the database is reachable."
        ) from exc
    _pool = pool
    _log.info("conwo db pool opened (min=%d max=%d)", min_size, max_size)


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def _get_pool() -> ConnectionPool:
    if _pool is None:
        # Lazy-open for scripts / tests that didn't go through the app lifespan.
        init_pool()
    assert _pool is not None
    return _pool


@contextmanager
def connection() -> Iterator[psycopg.Connection]:
    """Acquire a pooled connection (autocommit, Row factory, search_path set).

    Returned to the pool on exit; psycopg rolls back any open tx on exception.
    """
    with _get_pool().connection() as conn:
        yield conn


@contextmanager
def cursor() -> Iterator[psycopg.Cursor]:
    """Acquire a pooled connection + cursor in one with-block."""
    with connection() as conn:
        with conn.cursor() as cur:
            yield cur


# ── Migration runner ────────────────────────────────────────────────────────
def init_db() -> None:
    """Apply all migrations/*.sql in sorted order. Idempotent.

    Each migration must be written idempotently (CREATE ... IF NOT EXISTS,
    ADD COLUMN IF NOT EXISTS, CREATE EXTENSION IF NOT EXISTS) so re-running on
    every startup is a no-op once applied — mirroring the old per-store
    `executescript(_SCHEMA)` behavior.
    """
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not files:
        _log.warning("init_db: no migration files found in %s", MIGRATIONS_DIR)
        return
    # Postgres advisory lock so concurrent replica startups serialize — otherwise
    # simultaneous `CREATE TABLE IF NOT EXISTS` can race on pg_type. The lock key
    # is an arbitrary fixed constant unique to Conwo migrations.
    _MIGRATION_LOCK_KEY = 824671
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_lock(%s)", (_MIGRATION_LOCK_KEY,))
        try:
            for path in files:
                sql = path.read_text(encoding="utf-8")
                if not sql.strip():
                    continue
                with conn.cursor() as cur:
                    cur.execute(sql)
                _log.info("init_db: applied %s", path.name)
        finally:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(%s)", (_MIGRATION_LOCK_KEY,))
