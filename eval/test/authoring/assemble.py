#!/usr/bin/env python3
"""Merge the verified and supplementary per-conversation question files
(verified/, supplement/) into eval/test/private_questions.json.

Pipeline: drafts/ -> verified/ (answer/evidence/uniqueness checked) and
supplement/ (new facts in publicly cited turns) -> this script.
The incomplete calibrated/ drafts are not the released question set.

    python3 -I eval/test/authoring/assemble.py
"""
from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST_CONVERSATIONS = ("conv-30", "conv-42", "conv-43", "conv-47", "conv-48", "conv-50")


def main() -> None:
    questions = []
    for cid in TEST_CONVERSATIONS:
        batch = []
        for part, label in (("verified", "main"), ("supplement", "supplement")):
            data = json.loads((HERE / part / f"{cid}.json").read_text())
            assert data["conversation_id"] == cid
            batch.extend({**q, "batch": label} for q in data["questions"])
        # IDs and order are visible to retrievers: shuffle (fixed seed) so neither
        # reveals the authoring batch.
        random.Random(f"private-order:{cid}").shuffle(batch)
        for index, q in enumerate(batch):
            questions.append(
                {
                    "question_id": f"{cid}:p{index}",
                    "conversation_id": cid,
                    "question": q["question"].strip(),
                    "answer": str(q["answer"]).strip(),
                    "category": q["category"],
                    "evidence_entry_ids": list(q["evidence_entry_ids"]),
                    "support": q.get("support", ""),
                    "batch": q["batch"],
                }
            )
    out = {
        "description": (
            "PRIVATE hidden-test questions for six held-out LoCoMo conversations. Written in LoCoMo's style and "
            "four categories, then verified against the conversation (answer supported by the evidence turns, "
            "evidence complete, one correct answer). batch=main questions cite no turn that any public LoCoMo "
            "question cites; batch=supplement questions cite at least one such turn but ask facts no public "
            "question asks, so public labels are neither a positive nor a negative prior. Never published; keep "
            "only in eval/test/."
        ),
        "questions": questions,
    }
    path = HERE.parent / "private_questions.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    print(len(questions), dict(sorted(Counter(q["category"] for q in questions).items())),
          dict(Counter(q["conversation_id"] for q in questions)))


if __name__ == "__main__":
    main()
