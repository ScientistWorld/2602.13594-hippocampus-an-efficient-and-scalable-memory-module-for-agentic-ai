#!/usr/bin/env python3
"""Structural check of a private-question file for one held-out conversation.

    python3 -I eval/test/authoring/check_draft.py conv-30 eval/test/authoring/drafts/conv-30.json

Checks: JSON shape, categories, every evidence id is a real turn of this
conversation and not a public-evidence turn (with --supplement: at least one
evidence turn IS a public-evidence turn), no duplicate questions, answer not
empty. Prints per-category counts. Exit code 1 on any error.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CATEGORIES = {"single_hop", "multi_hop", "temporal", "open_domain"}


def main() -> None:
    conv, path = sys.argv[1], Path(sys.argv[2])
    # --supplement: every question must cite at least one PUBLIC-EVIDENCE turn.
    supplement = "--supplement" in sys.argv[3:]
    dump = (HERE / "dumps" / f"{conv}.txt").read_text()
    turns = set(re.findall(r"^\[(conv-\d+:D\d+:\d+)\]", dump, flags=re.M))
    public = set(json.loads((HERE / "dumps" / f"{conv}.public_evidence.json").read_text()))
    data = json.loads(path.read_text())
    errors = []
    if data.get("conversation_id") != conv:
        errors.append(f"conversation_id must be {conv}")
    seen = set()
    counts = Counter()
    for i, q in enumerate(data.get("questions", [])):
        tag = f"q[{i}] {q.get('question', '')[:60]!r}"
        for key in ("question", "answer", "category", "evidence_entry_ids"):
            if key not in q:
                errors.append(f"{tag}: missing {key}")
        if q.get("category") not in CATEGORIES:
            errors.append(f"{tag}: bad category {q.get('category')!r}")
        counts[q.get("category")] += 1
        ev = q.get("evidence_entry_ids") or []
        if not ev or not isinstance(ev, list):
            errors.append(f"{tag}: empty evidence")
        if len(set(ev)) != len(ev):
            errors.append(f"{tag}: duplicate evidence ids")
        for eid in ev:
            if eid not in turns:
                errors.append(f"{tag}: unknown evidence id {eid}")
            elif eid in public and not supplement:
                errors.append(f"{tag}: {eid} is a PUBLIC-EVIDENCE turn")
        if supplement and not any(eid in public for eid in ev):
            errors.append(f"{tag}: supplement question cites no PUBLIC-EVIDENCE turn")
        if not str(q.get("answer", "")).strip():
            errors.append(f"{tag}: empty answer")
        key = re.sub(r"\W+", " ", str(q.get("question", "")).lower()).strip()
        if key in seen:
            errors.append(f"{tag}: duplicate question")
        seen.add(key)
    print(f"{conv}: {sum(counts.values())} questions {dict(sorted(counts.items()))}")
    for e in errors:
        print("ERROR", e)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
