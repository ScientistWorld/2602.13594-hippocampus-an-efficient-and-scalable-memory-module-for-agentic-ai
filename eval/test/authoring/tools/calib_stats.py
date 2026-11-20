#!/usr/bin/env python3
"""Style calibration stats: question length and question-evidence word overlap
per category, private files vs the public LoCoMo train questions (no text printed,
no retriever is run).

    python3 -I eval/test/authoring/tools/calib_stats.py calibrated [conv-42 conv-50 ...]

Reads <part>/verified/conv-*.json and <part>/supplement/conv-*.json under
eval/test/authoring/ (part = "." for the uncalibrated files). Reports, per
category: n, mean content words per question ("len"), mean overlap (fraction of
the question's content words that occur in its evidence turns), and the share
of questions with overlap >= 0.8. Targets are the train values printed first.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from baseline.lexical_retriever import tokenize  # noqa: E402

sys.path.insert(0, str(HERE.parent))
import prepare_test_split as P  # noqa: E402


def stem(t: str) -> str:
    for s in ("ing", "ed", "es", "s"):
        if t.endswith(s) and len(t) - len(s) >= 3:
            return t[: -len(s)]
    return t


def measure(question: str, ev_texts: list[str], names: set[str]) -> tuple[int, float]:
    words = [t for t in tokenize(question) if t not in names]
    q = {stem(t) for t in words}
    if not q:
        return len(words), 0.0
    ev = {stem(t) for txt in ev_texts for t in tokenize(txt)}
    return len(words), len(q & ev) / len(q)


def summarize(rows: list[tuple[int, float]]) -> dict:
    n = len(rows)
    return {
        "n": n,
        "len": round(sum(r[0] for r in rows) / n, 2),
        "overlap": round(sum(r[1] for r in rows) / n, 3),
        "share_ov_ge_0.8": round(sum(r[1] >= 0.8 for r in rows) / n, 3),
    }


def main() -> None:
    part = sys.argv[1] if len(sys.argv) > 1 else "."
    only = set(sys.argv[2:])
    train = json.loads((ROOT / "data" / "locomo_train.json").read_text())
    ent = {e["entry_id"]: e for c in train["conversations"] for e in c["entries"]}
    names_tr = {c["conversation_id"]: {s.lower() for s in c["speakers"]} for c in train["conversations"]}
    tr = defaultdict(list)
    for q in train["questions"]:
        r = measure(q["question"], [ent[e]["text"] for e in q["evidence_entry_ids"]], names_tr[q["conversation_id"]])
        tr[q["category"]].append(r)
        tr["ALL"].append(r)
    print("TARGET train (public LoCoMo):")
    for k, v in sorted(tr.items()):
        print(f"  {k:12s} {summarize(v)}")

    src_path = ROOT / "tmp" / "locomo_src" / "locomo10.json"
    samples = {s["sample_id"]: s for s in json.loads(src_path.read_text())}
    pr = defaultdict(list)
    for batch in ("verified", "supplement"):
        for f in sorted((HERE / part / batch).glob("conv-*.json")):
            d = json.loads(f.read_text())
            cid = d["conversation_id"]
            if only and cid not in only:
                continue
            conv = P.convert_conversation(samples[cid])
            e2 = {e["entry_id"]: e for e in conv["entries"]}
            names = {s.lower() for s in conv["speakers"]}
            for q in d["questions"]:
                r = measure(q["question"], [e2[e]["text"] for e in q["evidence_entry_ids"]], names)
                pr[q["category"]].append(r)
                pr["ALL"].append(r)
    label = f"{part} {' '.join(sorted(only)) or 'all conversations'}"
    print(f"PRIVATE ({label}):")
    for k, v in sorted(pr.items()):
        print(f"  {k:12s} {summarize(v)}")


if __name__ == "__main__":
    main()
