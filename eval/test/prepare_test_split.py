#!/usr/bin/env python3
"""Build the hidden LoCoMo test split used only by eval/test/.

Fetches the pinned public LoCoMo release (or reads a local copy), keeps the six
held-out conversations, and writes eval/test/locomo_test.json with questions,
answers and turn-level evidence labels. This file is the only place in the
workspace that can produce the test labels.

Usage:
    python eval/test/prepare_test_split.py [--source /path/to/locomo10.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import urllib.request
from pathlib import Path


TEST_CONVERSATIONS = ("conv-30", "conv-42", "conv-43", "conv-47", "conv-48", "conv-50")
SOURCE_URL = (
    "https://raw.githubusercontent.com/snap-research/locomo/"
    "cbfbc1dba6bc53d00625212a0f22d55ffee7c1fc/data/locomo10.json"
)
SOURCE_SHA256 = "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4"
# LoCoMo category codes. Category 5 (adversarial / unanswerable) is excluded,
# matching the four task groups reported in the paper's LoCoMo table.
CATEGORY_NAMES = {1: "multi_hop", 2: "temporal", 3: "open_domain", 4: "single_hop"}
_DIA_RE = re.compile(r"^D:?(\d+):0*(\d+)$")


def _session_keys(conversation: dict) -> list[int]:
    numbers = []
    for key, value in conversation.items():
        match = re.fullmatch(r"session_(\d+)", key)
        if match and isinstance(value, list):
            numbers.append(int(match.group(1)))
    return sorted(numbers)


def _normalise_dia_id(raw: str) -> str | None:
    match = _DIA_RE.match(raw.strip())
    if not match:
        return None
    return f"D{int(match.group(1))}:{int(match.group(2))}"


def convert_sample(sample: dict) -> tuple[dict, list[dict]]:
    conv_id = sample["sample_id"]
    conversation = sample["conversation"]
    entries = []
    known = set()
    for session in _session_keys(conversation):
        date_time = conversation.get(f"session_{session}_date_time", "")
        for turn_index, turn in enumerate(conversation[f"session_{session}"], start=1):
            dia_id = _normalise_dia_id(turn["dia_id"]) or turn["dia_id"]
            text = f"{turn['speaker']}: {turn['text']}"
            if turn.get("blip_caption"):
                text += f" [shares image: {turn['blip_caption']}]"
            entry_id = f"{conv_id}:{dia_id}"
            known.add(entry_id)
            entries.append(
                {
                    "entry_id": entry_id,
                    "session": session,
                    "turn": turn_index,
                    "date_time": date_time,
                    "speaker": turn["speaker"],
                    "text": text,
                }
            )

    questions = []
    for q_index, qa in enumerate(sample["qa"]):
        category = CATEGORY_NAMES.get(qa.get("category"))
        if category is None or "answer" not in qa:
            continue
        evidence = []
        for raw in qa.get("evidence", []):
            for part in re.split(r"[;,\s]+", str(raw)):
                dia_id = _normalise_dia_id(part) if part else None
                entry_id = f"{conv_id}:{dia_id}" if dia_id else None
                if entry_id in known and entry_id not in evidence:
                    evidence.append(entry_id)
        if not evidence:
            continue
        questions.append(
            {
                "question_id": f"{conv_id}:q{q_index}",
                "conversation_id": conv_id,
                "question": qa["question"],
                "answer": str(qa["answer"]),
                "evidence_entry_ids": evidence,
                "category": category,
            }
        )
    speakers = [conversation.get("speaker_a", ""), conversation.get("speaker_b", "")]
    return {"conversation_id": conv_id, "speakers": speakers, "entries": entries}, questions


def build_split(source: Path, conversation_ids: tuple[str, ...]) -> dict:
    samples = json.loads(source.read_text())
    by_id = {sample["sample_id"]: sample for sample in samples}
    missing = [cid for cid in conversation_ids if cid not in by_id]
    if missing:
        raise ValueError(f"LoCoMo source is missing conversations: {missing}")
    conversations, questions = [], []
    for cid in conversation_ids:
        conv, qs = convert_sample(by_id[cid])
        conversations.append(conv)
        questions.extend(qs)
    return {
        "source": "LoCoMo locomo10.json (snap-research/locomo @ cbfbc1d)",
        "split": "test",
        "conversations": conversations,
        "questions": questions,
    }


def fetch_source(destination: Path) -> Path:
    with urllib.request.urlopen(SOURCE_URL, timeout=120) as response:
        payload = response.read()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError(f"LoCoMo checksum mismatch: {digest}")
    destination.write_bytes(payload)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=None, help="optional local locomo10.json")
    parser.add_argument("--output", default=str(Path(__file__).with_name("locomo_test.json")))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(args.source) if args.source else fetch_source(Path(tmp) / "locomo10.json")
        data = build_split(source, TEST_CONVERSATIONS)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=1) + "\n")
    print(f"wrote {output}: {len(data['conversations'])} conversations, {len(data['questions'])} questions")


if __name__ == "__main__":
    main()
