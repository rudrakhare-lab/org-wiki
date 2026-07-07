"""Eval harness metrics — recall@k, MRR, section hits."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import eval_wiki_retrieval as ev


def test_recall_at_k():
    got = ["a.md", "b.md", "c.md"]
    assert ev.recall_at_k(got, expected=["b.md"], k=5) == 1.0
    assert ev.recall_at_k(got, expected=["z.md"], k=5) == 0.0
    assert ev.recall_at_k(got, expected=["b.md", "z.md"], k=5) == 0.5


def test_mrr():
    assert ev.mrr(["a.md", "b.md"], expected=["b.md"]) == 0.5
    assert ev.mrr(["x.md"], expected=["y.md"]) == 0.0


def test_section_hit_rate():
    got_anchors = ["a.md#one", "b.md#two"]
    assert ev.section_hit(got_anchors, ["b.md#two"]) is True
    assert ev.section_hit(got_anchors, ["b.md#three"]) is False


def test_golden_loader_validates_schema(tmp_path):
    f = tmp_path / "g.jsonl"
    f.write_text('{"question": "q", "expected_pages": ["modules/a.md"]}\n')
    items = ev.load_golden(f)
    assert items[0]["question"] == "q"
