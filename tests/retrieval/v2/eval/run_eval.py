"""Run the eval set against the v2 pipeline; print recall@10 and abstention rate."""
import json, os, sys
from pathlib import Path

def main() -> int:
    here = Path(__file__).parent
    qs = json.loads((here / "queries.json").read_text())
    sys.path.insert(0, str(here.parent.parent.parent.parent))  # repo root
    from backend.retrieval.v2.pipeline import search
    abstained = 0; hits = 0; graded = 0
    for item in qs:
        r = search(item["q"])
        if r.abstain:
            abstained += 1
            print(f"[ABSTAIN] {item['q']}"); continue
        expected = set(item.get("expected_any_of") or [])
        if expected:
            graded += 1
            got = {t["key"] for t in r.tickets}
            if expected & got:
                hits += 1
                print(f"[HIT]     {item['q']}  → {sorted(expected&got)}")
            else:
                print(f"[MISS]    {item['q']}  expected {sorted(expected)} got {sorted(got)}")
        else:
            print(f"[OK]      {item['q']}  top={r.tickets[0]['key'] if r.tickets else '-'}")
    print(f"\nabstention_rate={abstained}/{len(qs)} = {100*abstained//max(1,len(qs))}%")
    if graded:
        print(f"recall@10={hits}/{graded} = {100*hits//graded}%")
    return 0

if __name__ == "__main__":
    sys.exit(main())
