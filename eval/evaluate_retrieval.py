#!/usr/bin/env python3
"""Development evaluator behind scripts/evaluate.sh (writes scoring/scores.json).

Uses the train-split protocol in eval/train/evaluate_retrieval.py: with no
arguments it runs every registered retriever (scripts/retrievers/*.sh) on the
visible LoCoMo training conversations; with --artifacts it scores saved
retrieval JSONL files produced on data/locomo_train.json.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.train import evaluate_retrieval as train_protocol  # noqa: E402


if __name__ == "__main__":
    if not any(arg == "--output" or arg.startswith("--output=") for arg in sys.argv[1:]):
        sys.argv[1:1] = ["--output", str(ROOT / "scoring" / "scores.json")]
    train_protocol.main()
