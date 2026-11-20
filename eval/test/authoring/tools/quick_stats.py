"""Metrics-only calibration of draft/verified question files (prints no question text).

    python3 -I eval/test/authoring/tools/quick_stats.py drafts|verified
"""
import json, sys, re
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from baseline.lexical_retriever import BM25Index  # noqa
sys.path.insert(0, str(ROOT / "redteam" / "hardening"))
import better_bm25_context as ctx  # noqa

src = json.loads((ROOT / "tmp/locomo_src/locomo10.json").read_text())
sys.path.insert(0, str(HERE.parent))
import prepare_test_split as P  # noqa
samples = {s["sample_id"]: s for s in src}
kind = sys.argv[1]
public = json.loads((ROOT / "redteam/hardening/shortcuts/public_locomo_heldout_qa.json").read_text())["questions"]
pub_turns = {e for p in public for e in p["evidence_entry_ids"]}
tot = defaultdict(list)
groups = defaultdict(list)
for part in kind.split("+"):
    for f in sorted((HERE / part).glob("conv-*.json")):
        d = json.loads(f.read_text())
        groups[d["conversation_id"]].extend(d["questions"])
for cid in sorted(groups):
    d = {"conversation_id": cid, "questions": groups[cid]}
    conv = P.convert_conversation(samples[cid])
    ents = conv["entries"]
    bm = BM25Index(ents); cx = ctx.Index(ents)
    res = defaultdict(list)
    for q in d["questions"]:
        gold = set(q["evidence_entry_ids"])
        r = lambda ids: len(gold & set(ids[:10])) / len(gold)
        top = bm.search(q["question"], 40)
        res["bm25"].append(r(top))
        res["bm25_avoid_public"].append(r([e for e in top if e not in pub_turns]))
        res["bm25_prior_public"].append(r(([e for e in top[:30] if e in pub_turns] + [e for e in top[:30] if e not in pub_turns])))
        res["bm25_context"].append(r(cx.search(q["question"], 10)))
        res["n_ev"].append(len(gold))
        res["cat_" + q["category"] + "_bm25"].append(r(top))
    for k, v in res.items():
        tot[k] += v
    print(cid, len(d["questions"]), {k: round(100 * sum(v) / len(v), 1) for k, v in res.items() if k != "n_ev"},
          "avg_ev", round(sum(res["n_ev"]) / len(res["n_ev"]), 2))
print("ALL", len(tot["bm25"]), {k: round(100 * sum(v) / len(v), 1) for k, v in tot.items() if k != "n_ev"})
