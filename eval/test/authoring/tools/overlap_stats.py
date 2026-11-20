"""Question-evidence lexical overlap, private drafts vs public LoCoMo train questions (no text printed).

Overlap = fraction of the question's content words (stop words and speaker
names removed) that occur in the text of its evidence turns.
    python3 -I eval/test/authoring/tools/overlap_stats.py drafts|verified [--flag 0.8]
"""
import json, sys, re
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from baseline.lexical_retriever import tokenize  # stop-word filtered tokens  # noqa
sys.path.insert(0, str(HERE.parent))
import prepare_test_split as P  # noqa


def stem(t):
    for s in ("ing", "ed", "es", "s"):
        if t.endswith(s) and len(t) - len(s) >= 3:
            return t[: -len(s)]
    return t


def overlap(question, ev_texts, names):
    q = {stem(t) for t in tokenize(question) if t not in names}
    if not q:
        return 0.0
    ev = {stem(t) for txt in ev_texts for t in tokenize(txt)}
    return len(q & ev) / len(q)


def summarize(vals):
    vals = sorted(vals)
    n = len(vals)
    return {"n": n, "mean": round(sum(vals) / n, 3), "median": round(vals[n // 2], 3),
            "share_ge_0.8": round(sum(v >= 0.8 for v in vals) / n, 3), "share_eq_1": round(sum(v >= 0.999 for v in vals) / n, 3)}


train = json.loads((ROOT / "data/locomo_train.json").read_text())
ent = {e["entry_id"]: e for c in train["conversations"] for e in c["entries"]}
names_tr = {c["conversation_id"]: {s.lower() for s in c["speakers"]} for c in train["conversations"]}
tr = defaultdict(list)
for q in train["questions"]:
    v = overlap(q["question"], [ent[e]["text"] for e in q["evidence_entry_ids"]], names_tr[q["conversation_id"]])
    tr[q["category"]].append(v); tr["ALL"].append(v)
print("TRAIN(public LoCoMo)", {k: summarize(v) for k, v in sorted(tr.items())})

kind = sys.argv[1]
src = {s["sample_id"]: s for s in json.loads((ROOT / "tmp/locomo_src/locomo10.json").read_text())}
pr = defaultdict(list)
for f in sorted((HERE / kind).glob("conv-*.json")):
    d = json.loads(f.read_text()); cid = d["conversation_id"]
    conv = P.convert_conversation(src[cid]); e2 = {e["entry_id"]: e for e in conv["entries"]}
    names = {s.lower() for s in conv["speakers"]}
    for q in d["questions"]:
        v = overlap(q["question"], [e2[e]["text"] for e in q["evidence_entry_ids"]], names)
        pr[q["category"]].append(v); pr["ALL"].append(v)
print("PRIVATE", kind, {k: summarize(v) for k, v in sorted(pr.items())})
