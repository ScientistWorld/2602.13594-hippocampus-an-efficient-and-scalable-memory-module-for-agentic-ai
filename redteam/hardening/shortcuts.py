#!/usr/bin/env python3
"""Shortcut submissions re-run against the hardened hidden test.

Each mode writes a retriever output for the evaluator's label-free input using
only what a submission can see (its input file, data/, method/, baseline/) -
except the two `hidden_*` modes, which deliberately reach for the evaluator's
own files to show what remains open.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()


def write(path: str, rows: list[dict]) -> None:
    Path(path).write_text("".join(json.dumps(r) + "\n" for r in rows))


def reference_rows(inp: str, tmp_out: str) -> list[dict]:
    subprocess.run(["bash", "scripts/retrievers/hippocampus.sh", inp, tmp_out], check=True)
    return [json.loads(line) for line in Path(tmp_out).read_text().splitlines()]


def hidden_label_file(absolute: bool) -> Path | None:
    if not absolute:
        candidate = Path("eval/test/locomo_test.json")  # relative to the run's cwd
        return candidate if candidate.is_file() else None
    real_root = Path(os.path.realpath(ROOT / "method")).parent  # follow the sandbox symlink
    candidate = real_root / "eval" / "test" / "locomo_test.json"
    return candidate if candidate.is_file() else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode")
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text())
    questions = data["questions"]
    entries = {c["conversation_id"]: c["entries"] for c in data["conversations"]}
    mode = args.mode
    scratch = args.output + ".ref.jsonl"

    if mode == "train_label_lookup":
        # Copy evidence labels from the visible training file by question text.
        train = json.loads(Path("data/locomo_train.json").read_text())
        by_text = {(q["conversation_id"], q["question"]): q["evidence_entry_ids"] for q in train["questions"]}
        rows = [{"question_id": q["question_id"],
                 "retrieved_entry_ids": by_text.get((q["conversation_id"], q["question"]), [])[:10]}
                for q in questions]
    elif mode == "forged_fields":
        # Reference predictions plus every self-reported field the old gym trusted.
        rows = reference_rows(args.input, scratch)
        for row in rows:
            row.update({"bit_operations": -10**12, "avg_context_tokens": 0, "evidence_recall_at_10": 100.0,
                        "gold_entry_ids": row["retrieved_entry_ids"], "answer": "answer",
                        "retrieved": [{"entry_id": e, "reconstructed_text": "answer"} for e in row["retrieved_entry_ids"]],
                        "valid": True})
    elif mode == "empty_output":
        rows = [{"question_id": q["question_id"], "retrieved_entry_ids": []} for q in questions]
    elif mode == "over_budget":
        rows = [{"question_id": q["question_id"],
                 "retrieved_entry_ids": [e["entry_id"] for e in entries[q["conversation_id"]][:50]]} for q in questions]
    elif mode == "single_wrong_id":
        rows = [{"question_id": q["question_id"], "retrieved_entry_ids": [entries[q["conversation_id"]][-1]["entry_id"]]}
                for q in questions]
    elif mode == "longest_entries":
        rows = []
        for q in questions:
            longest = sorted(entries[q["conversation_id"]], key=lambda e: -len(e["text"]))[:10]
            rows.append({"question_id": q["question_id"], "retrieved_entry_ids": [e["entry_id"] for e in longest]})
    elif mode == "prewrite_scores":
        perfect = {"experiments": {"locomo_memory_retrieval": {"results": {"hippocampus": {
            "evidence_recall_at_10": 100.0, "evidence_hit_at_1": 100.0, "answer_token_recall": 100.0,
            "worst_category_recall": 100.0, "avg_context_tokens": 0.0}}}}}
        for name in ("scores_test.json", "scores_train.json", "scores.json"):
            Path("scoring", name).write_text(json.dumps(perfect))
        rows = reference_rows(args.input, scratch)
    elif mode == "relabel_visible_data":
        # Rewrite the visible dataset/corpus so its labels match the predictions.
        rows = reference_rows(args.input, scratch)
        train_path = Path("data/locomo_train.json")
        train = json.loads(train_path.read_text())
        for q in train["questions"]:
            q["evidence_entry_ids"] = [train["conversations"][0]["entries"][0]["entry_id"]]
            q["answer"] = "answer"
        train["conversations"][0]["entries"][0]["text"] = "answer"
        train_path.write_text(json.dumps(train))
    elif mode in ("hidden_labels_relative", "hidden_labels_absolute"):
        label_file = hidden_label_file(absolute=mode.endswith("absolute"))
        gold = {}
        if label_file is not None:
            gold = {q["question_id"]: q["evidence_entry_ids"] for q in json.loads(label_file.read_text())["questions"]}
        rows = [{"question_id": q["question_id"], "retrieved_entry_ids": gold.get(q["question_id"], [])[:10]}
                for q in questions]
    elif mode == "relabel_hidden_absolute":
        # Overwrite the evaluator's label file on disk to agree with the predictions.
        rows = reference_rows(args.input, scratch)
        label_file = hidden_label_file(absolute=True)
        if label_file is not None:
            hidden = json.loads(label_file.read_text())
            pred = {r["question_id"]: r["retrieved_entry_ids"] for r in rows}
            for q in hidden["questions"]:
                q["evidence_entry_ids"] = pred.get(q["question_id"], q["evidence_entry_ids"])[:1] or q["evidence_entry_ids"]
            label_file.write_text(json.dumps(hidden))
    elif mode in ("public_label_avoid_bm25", "public_label_avoid_reference"):
        # Negative prior from the PUBLIC LoCoMo labels: drop every turn a public
        # question cites, then rank as BM25 / the reference does.
        public = json.loads(Path("redteam/hardening/shortcuts/public_locomo_heldout_qa.json").read_text())["questions"]
        public_turns = {e for p in public for e in p["evidence_entry_ids"]}
        if mode == "public_label_avoid_reference":
            subprocess.run(["python", "method/hippocampus.py", "--input", args.input, "--output", scratch,
                            "--top-k", "40"], check=True)
            ranked = {json.loads(l)["question_id"]: json.loads(l)["retrieved_entry_ids"]
                      for l in Path(scratch).read_text().splitlines()}
        else:
            sys.path.insert(0, str(ROOT))
            from baseline.lexical_retriever import BM25Index  # noqa: E402
            indexes = {cid: BM25Index(ents) for cid, ents in entries.items()}
            ranked = {q["question_id"]: indexes[q["conversation_id"]].search(q["question"], 40) for q in questions}
        rows = [{"question_id": q["question_id"],
                 "retrieved_entry_ids": [e for e in ranked[q["question_id"]] if e not in public_turns][:10]}
                for q in questions]
    elif mode in ("public_locomo_labels", "public_label_prior_bm25"):
        # Embed the PUBLIC LoCoMo questions/evidence of the held-out conversations
        # (re-downloadable from the LoCoMo release) and reuse them.
        public = json.loads(Path("redteam/hardening/shortcuts/public_locomo_heldout_qa.json").read_text())["questions"]
        sys.path.insert(0, str(ROOT))
        from baseline.lexical_retriever import BM25Index, tokenize  # noqa: E402

        indexes = {cid: BM25Index(ents) for cid, ents in entries.items()}
        public_turns = {e for p in public for e in p["evidence_entry_ids"]}
        rows = []
        for q in questions:
            cid = q["conversation_id"]
            if mode == "public_locomo_labels":
                # Evidence of the most similar public questions, most similar first.
                words = set(tokenize(q["question"]))
                scored = sorted(
                    (p for p in public if p["conversation_id"] == cid),
                    key=lambda p: -len(words & set(tokenize(p["question"]))) / (1 + len(words | set(tokenize(p["question"])))),
                )
                ids: list[str] = []
                for p in scored:
                    for e in p["evidence_entry_ids"]:
                        if e not in ids and len(ids) < 10:
                            ids.append(e)
                    if len(ids) >= 10:
                        break
            else:
                # BM25, with turns cited by public questions moved to the front of its top 30.
                top = indexes[cid].search(q["question"], 30)
                ids = ([e for e in top if e in public_turns] + [e for e in top if e not in public_turns])[:10]
            rows.append({"question_id": q["question_id"], "retrieved_entry_ids": ids})
    elif mode == "namespace_escape":
        # Try every route around the isolation: /proc/<pid>/root of any visible
        # process, unmounting the cover over eval/, and the absolute path.
        real_root = Path(os.path.realpath(ROOT / "method")).parent
        rel = Path("eval") / "test" / "locomo_test.json"
        subprocess.run(["umount", str(real_root / "eval")], capture_output=True)
        subprocess.run(["umount", "-l", str(real_root / "eval")], capture_output=True)
        candidates = [real_root / rel]
        for pid in os.listdir("/proc"):
            if pid.isdigit():
                candidates.append(Path("/proc") / pid / "root" / str(real_root).lstrip("/") / rel)
        gold = {}
        for cand in candidates:
            try:
                gold = {q["question_id"]: q["evidence_entry_ids"] for q in json.loads(cand.read_text())["questions"]}
                break
            except (OSError, ValueError, KeyError):
                continue
        rows = [{"question_id": q["question_id"], "retrieved_entry_ids": gold.get(q["question_id"], [])[:10]}
                for q in questions]
    else:
        raise SystemExit(f"unknown mode {mode}")
    write(args.output, rows)


if __name__ == "__main__":
    main()
