#!/usr/bin/env python3
"""Better variant: HIPPOCAMPUS candidates re-ranked by BM25 over their reconstructed text.

The paper's pipeline (Hamming-ball scan + metadata validation) proposes the top
30 entries; each candidate's content is reconstructed from the Content DWM and
re-ranked with BM25 (IDF from the conversation's memory). Labels are never read.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "method"))
sys.path.insert(0, str(ROOT / "baseline"))
from hippocampus import HippocampusMemory  # noqa: E402
from lexical_retriever import BM25Index  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--candidates", type=int, default=30)
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text())
    memories, indexes = {}, {}
    for conv in data["conversations"]:
        memory = HippocampusMemory(512, 32, radius=8, window=1, query_window=0, seed=13)
        memory.build(conv["entries"])
        memories[conv["conversation_id"]] = memory
        indexes[conv["conversation_id"]] = BM25Index(conv["entries"])
    with open(args.output, "w") as handle:
        for q in data["questions"]:
            memory = memories[q["conversation_id"]]
            candidates = memory.retrieve(q["question"], top_k=args.candidates)["retrieved_entry_ids"]
            index = indexes[q["conversation_id"]]
            position = {entry_id: i for i, entry_id in enumerate(index.ids)}
            ranked_all = index.search(q["question"], top_k=len(index.ids))
            order = {entry_id: rank for rank, entry_id in enumerate(ranked_all)}
            reranked = sorted(candidates, key=lambda e: (order[e], position[e]))[:10]
            handle.write(json.dumps({"question_id": q["question_id"], "retrieved_entry_ids": reranked}) + "\n")


if __name__ == "__main__":
    main()
