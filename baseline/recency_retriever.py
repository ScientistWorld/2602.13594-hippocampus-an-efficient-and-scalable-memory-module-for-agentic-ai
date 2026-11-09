#!/usr/bin/env python3
"""Recency baseline: return the most recent memory entries of the conversation.

Stands in for lightweight memory systems that keep only the latest context
without any semantic index. Same I/O contract as every gym retriever:
    python baseline/recency_retriever.py --input <memory.json> --output <results.jsonl>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def run(args: argparse.Namespace) -> None:
    dataset = json.loads(Path(args.input).read_text())
    latest = {}
    for conversation in dataset["conversations"]:
        entries = sorted(conversation["entries"], key=lambda e: (e["session"], e["turn"]), reverse=True)
        latest[conversation["conversation_id"]] = [entry["entry_id"] for entry in entries[: args.top_k]]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w") as handle:
        for item in dataset["questions"]:
            row = {"question_id": item["question_id"], "retrieved_entry_ids": latest[item["conversation_id"]]}
            handle.write(json.dumps(row) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--top-k", type=int, default=10)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
