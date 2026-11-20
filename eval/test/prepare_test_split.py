#!/usr/bin/env python3
"""Build the hidden test split used only by eval/test/.

Memories: the dialogue turns of six held-out LoCoMo conversations, taken from
the pinned public LoCoMo release (fetched, or read from a local copy).

Questions and labels: eval/test/private_questions.json, a PRIVATE question set
written for these conversations in LoCoMo's style and four categories
(single-hop, multi-hop, temporal, open-domain). Each question was checked to be
answerable from its evidence turns. The questions were never published, so
re-downloading LoCoMo does not reveal the test labels. The public LoCoMo
questions of these conversations are not used. Two batches:
  main        no evidence turn is cited by any public LoCoMo question;
  supplement  at least one evidence turn IS cited by a public LoCoMo question,
              but the question asks a fact no public question asks.
Together they make "turns cited by public LoCoMo questions" useless both as a
positive prior (most labels avoid them) and as a negative prior (removing them
loses the supplement batch).

Writes eval/test/locomo_test.json. This directory is the only place in the
workspace that holds or can produce the test labels.

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
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
TEST_CONVERSATIONS = ("conv-30", "conv-42", "conv-43", "conv-47", "conv-48", "conv-50")
PRIVATE_QUESTIONS = HERE / "private_questions.json"
SOURCE_URL = (
    "https://raw.githubusercontent.com/snap-research/locomo/"
    "cbfbc1dba6bc53d00625212a0f22d55ffee7c1fc/data/locomo10.json"
)
SOURCE_SHA256 = "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4"
CATEGORIES = ("multi_hop", "open_domain", "single_hop", "temporal")
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


def convert_conversation(sample: dict) -> dict:
    conv_id = sample["sample_id"]
    conversation = sample["conversation"]
    entries = []
    for session in _session_keys(conversation):
        date_time = conversation.get(f"session_{session}_date_time", "")
        for turn_index, turn in enumerate(conversation[f"session_{session}"], start=1):
            dia_id = _normalise_dia_id(turn["dia_id"]) or turn["dia_id"]
            text = f"{turn['speaker']}: {turn['text']}"
            if turn.get("blip_caption"):
                text += f" [shares image: {turn['blip_caption']}]"
            entries.append(
                {
                    "entry_id": f"{conv_id}:{dia_id}",
                    "session": session,
                    "turn": turn_index,
                    "date_time": date_time,
                    "speaker": turn["speaker"],
                    "text": text,
                }
            )
    speakers = [conversation.get("speaker_a", ""), conversation.get("speaker_b", "")]
    return {"conversation_id": conv_id, "speakers": speakers, "entries": entries}


def public_evidence(sample: dict) -> set[str]:
    """Every turn cited as evidence by any public LoCoMo question (categories 1-5)."""
    out = set()
    for qa in sample["qa"]:
        for raw in qa.get("evidence", []):
            for part in re.split(r"[;,\s]+", str(raw)):
                dia_id = _normalise_dia_id(part) if part else None
                if dia_id:
                    out.add(f"{sample['sample_id']}:{dia_id}")
    return out


def build_split(source: Path, private_path: Path = PRIVATE_QUESTIONS) -> dict:
    samples = {sample["sample_id"]: sample for sample in json.loads(source.read_text())}
    missing = [cid for cid in TEST_CONVERSATIONS if cid not in samples]
    if missing:
        raise ValueError(f"LoCoMo source is missing conversations: {missing}")
    conversations = [convert_conversation(samples[cid]) for cid in TEST_CONVERSATIONS]
    known = {e["entry_id"]: c["conversation_id"] for c in conversations for e in c["entries"]}
    public = set().union(*(public_evidence(samples[cid]) for cid in TEST_CONVERSATIONS))

    private = json.loads(private_path.read_text())["questions"]
    seen_ids, seen_text = set(), set()
    for q in private:
        qid, cid = q["question_id"], q["conversation_id"]
        if qid in seen_ids:
            raise ValueError(f"duplicate question id {qid}")
        seen_ids.add(qid)
        key = (cid, re.sub(r"\W+", " ", q["question"].lower()).strip())
        if key in seen_text:
            raise ValueError(f"duplicate question text {qid}")
        seen_text.add(key)
        if cid not in TEST_CONVERSATIONS or q["category"] not in CATEGORIES or not str(q["answer"]).strip():
            raise ValueError(f"malformed question {qid}")
        if not q["evidence_entry_ids"] or len(set(q["evidence_entry_ids"])) != len(q["evidence_entry_ids"]):
            raise ValueError(f"bad evidence list for {qid}")
        for entry_id in q["evidence_entry_ids"]:
            if known.get(entry_id) != cid:
                raise ValueError(f"{qid}: evidence {entry_id} is not a turn of {cid}")
        cites_public = any(entry_id in public for entry_id in q["evidence_entry_ids"])
        if q.get("batch") == "main" and cites_public:
            raise ValueError(f"{qid}: main-batch evidence is cited by a public LoCoMo question")
        if q.get("batch") == "supplement" and not cites_public:
            raise ValueError(f"{qid}: supplement-batch question cites no publicly cited turn")
        if q.get("batch") not in ("main", "supplement"):
            raise ValueError(f"{qid}: unknown batch {q.get('batch')!r}")
    questions = [
        {key: q[key] for key in ("question_id", "conversation_id", "question", "answer", "evidence_entry_ids", "category")}
        for q in private
    ]
    return {
        "source": "Memories: LoCoMo locomo10.json (snap-research/locomo @ cbfbc1d). Questions: private set (eval/test/private_questions.json).",
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
    parser.add_argument("--output", default=str(HERE / "locomo_test.json"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(args.source) if args.source else fetch_source(Path(tmp) / "locomo10.json")
        data = build_split(source)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=1) + "\n")
    counts = Counter(q["category"] for q in data["questions"])
    print(f"wrote {output}: {len(data['conversations'])} conversations, {len(data['questions'])} private questions "
          f"{dict(sorted(counts.items()))}")


if __name__ == "__main__":
    main()
