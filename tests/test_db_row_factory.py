"""
Verifies backend.db.Row is a faithful sqlite3.Row clone.

This is the load-bearing piece of the SQLite->Postgres migration: the whole
codebase relies on sqlite3.Row's dual int/str indexing AND values-iteration.
If Row diverges, data corruption is silent (e.g. dict(zip(cols,row)) zipping
names against names). Each test compares Row behavior to a real sqlite3.Row.
"""
from __future__ import annotations

import sqlite3

import pytest

from backend.db import Row


def _sqlite_row(cols, vals):
    """Build a real sqlite3.Row with the given columns/values for comparison."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    select = ", ".join(f"? AS {c}" for c in cols)
    row = conn.execute(f"SELECT {select}", tuple(vals)).fetchone()
    conn.close()
    return row


COLS = ["email", "role", "created_at"]
VALS = ["a@b.com", "admin", "2026-01-01"]


def test_positional_indexing_matches_sqlite():
    ours = Row(COLS, VALS)
    ref = _sqlite_row(COLS, VALS)
    for i in range(len(COLS)):
        assert ours[i] == ref[i] == VALS[i]


def test_name_indexing_matches_sqlite():
    ours = Row(COLS, VALS)
    ref = _sqlite_row(COLS, VALS)
    for c in COLS:
        assert ours[c] == ref[c]


def test_dict_conversion_matches_sqlite():
    # dict(row) uses keys() + __getitem__ — the auth_store/conversation_store path.
    ours = dict(Row(COLS, VALS))
    ref = dict(_sqlite_row(COLS, VALS))
    expected = {"email": "a@b.com", "role": "admin", "created_at": "2026-01-01"}
    assert ours == ref == expected


def test_dict_zip_iterates_values_matches_sqlite():
    # dict(zip(cols, row)) — the jira_retriever / query_jira_ranked path.
    # Iterating the row MUST yield values, not column names.
    ours = dict(zip(COLS, Row(COLS, VALS)))
    ref = dict(zip(COLS, _sqlite_row(COLS, VALS)))
    expected = {"email": "a@b.com", "role": "admin", "created_at": "2026-01-01"}
    assert ours == ref == expected


def test_tuple_unpack_matches_sqlite():
    # a, b, c = row — the trace_store fetchall loop path.
    e1, r1, c1 = Row(COLS, VALS)
    e2, r2, c2 = _sqlite_row(COLS, VALS)
    assert (e1, r1, c1) == (e2, r2, c2) == tuple(VALS)


def test_list_of_values_matches_sqlite():
    assert list(Row(COLS, VALS)) == list(_sqlite_row(COLS, VALS)) == VALS


def test_len_matches_sqlite():
    assert len(Row(COLS, VALS)) == len(_sqlite_row(COLS, VALS)) == 3


def test_keys_matches_sqlite():
    assert Row(COLS, VALS).keys() == _sqlite_row(COLS, VALS).keys() == COLS


def test_fetchone_zero_index():
    # cur.fetchone()[0] — the COUNT(*) path in trace_store / jira_count.
    ours = Row(["c"], [42])
    ref = _sqlite_row(["c"], [42])
    assert ours[0] == ref[0] == 42


def test_duplicate_column_first_wins_matches_sqlite():
    # sqlite3.Row: on duplicate names, row[name] returns the FIRST.
    cols = ["x", "y", "x"]
    vals = [1, 2, 3]
    ours = Row(cols, vals)
    ref = _sqlite_row(cols, vals)
    assert ours["x"] == ref["x"] == 1
    assert ours[2] == ref[2] == 3  # positional still reaches the dup


def test_missing_key_raises_keyerror():
    with pytest.raises(KeyError):
        Row(COLS, VALS)["nonexistent"]


def test_null_values_preserved():
    ours = Row(["a", "b"], [None, "x"])
    assert ours["a"] is None
    assert dict(ours) == {"a": None, "b": "x"}
