"""ingest_batch store: batch+item lifecycle, counts, get shape, reconcile."""
import json
import pytest
from backend import ingest_batch


@pytest.fixture(autouse=True)
def clean(clean_db):
    yield


def _items(n):
    return [{"upload_id": f"u{i}", "filename": f"f{i}.pdf", "file_path": f"/tmp/u{i}/f{i}.pdf"}
            for i in range(n)]


def test_create_batch_queues_items():
    r = ingest_batch.create_batch("conwo", "admin@x.com", _items(3))
    assert r["total"] == 3
    got = ingest_batch.get_batch(r["batch_id"])
    assert got["batch"]["status"] == "running"
    assert len(got["items"]) == 3
    assert [i["status"] for i in got["items"]] == ["queued", "queued", "queued"]
    assert [i["ord"] for i in got["items"]] == [0, 1, 2]


def test_create_batch_rejects_empty():
    with pytest.raises(ValueError):
        ingest_batch.create_batch("conwo", "admin@x.com", [])


def test_status_and_counts_and_pages():
    r = ingest_batch.create_batch("conwo", "a@x.com", _items(2))
    items = ingest_batch.get_batch(r["batch_id"])["items"]
    ingest_batch.set_item_status(items[0]["id"], "done", page_paths=["wiki/modules/x.md"])
    ingest_batch.bump_counts(r["batch_id"], completed=1)
    ingest_batch.set_item_status(items[1]["id"], "failed", error="boom")
    ingest_batch.bump_counts(r["batch_id"], failed=1)
    ingest_batch.set_batch_status(r["batch_id"], "done")
    got = ingest_batch.get_batch(r["batch_id"])
    assert got["batch"]["completed"] == 1 and got["batch"]["failed"] == 1
    assert got["batch"]["status"] == "done"
    by_ord = {i["ord"]: i for i in got["items"]}
    assert by_ord[0]["status"] == "done" and json.loads(by_ord[0]["page_paths"]) == ["wiki/modules/x.md"]
    assert by_ord[1]["status"] == "failed" and by_ord[1]["error"] == "boom"


def test_list_queued_items_orders_and_filters():
    r = ingest_batch.create_batch("conwo", "a@x.com", _items(2))
    items = ingest_batch.get_batch(r["batch_id"])["items"]
    ingest_batch.set_item_status(items[0]["id"], "done")
    q = ingest_batch.list_queued_items(r["batch_id"])
    assert [i["ord"] for i in q] == [1]


def test_reconcile_interrupted_flips_running_and_inflight():
    r = ingest_batch.create_batch("conwo", "a@x.com", _items(2))
    items = ingest_batch.get_batch(r["batch_id"])["items"]
    ingest_batch.set_item_status(items[0]["id"], "writing")
    n = ingest_batch.reconcile_interrupted()
    assert n >= 1
    got = ingest_batch.get_batch(r["batch_id"])
    assert got["batch"]["status"] == "interrupted"
    assert {i["status"] for i in got["items"]} <= {"interrupted", "queued"}
    # the in-flight 'writing' item became 'interrupted'
    assert any(i["status"] == "interrupted" for i in got["items"])


def test_reconcile_does_not_touch_items_of_nonrunning_batches():
    r = ingest_batch.create_batch("conwo", "a@x.com",
        [{"upload_id": "u0", "filename": "f0.pdf", "file_path": "/tmp/f0.pdf"}])
    items = ingest_batch.get_batch(r["batch_id"])["items"]
    ingest_batch.set_item_status(items[0]["id"], "writing")
    ingest_batch.set_batch_status(r["batch_id"], "done")   # batch no longer running
    ingest_batch.reconcile_interrupted()
    got = ingest_batch.get_batch(r["batch_id"])
    assert got["items"][0]["status"] == "writing"          # untouched
    assert got["batch"]["status"] == "done"
