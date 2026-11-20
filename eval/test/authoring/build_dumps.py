#!/usr/bin/env python3
"""Write one plain-text reading dump per held-out conversation for question authoring.

Each dump lists every dialogue turn with its gym entry id, session date and
speaker. Turns cited as evidence by ANY public LoCoMo question (categories 1-5)
are tagged (PUBLIC-EVIDENCE): private questions must not use them, so public
LoCoMo labels give no help on the private test set. The public questions are
listed at the end so authors can avoid duplicating their facts.

    python -I eval/test/authoring/build_dumps.py --source locomo10.json --out-dir eval/test/authoring/dumps
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TEST_CONVERSATIONS = ("conv-30", "conv-42", "conv-43", "conv-47", "conv-48", "conv-50")
_DIA_RE = re.compile(r"^D:?(\d+):0*(\d+)$")


def norm(raw: str) -> str | None:
    m = _DIA_RE.match(raw.strip())
    return f"D{int(m.group(1))}:{int(m.group(2))}" if m else None


def public_evidence(sample: dict) -> set[str]:
    conv_id = sample["sample_id"]
    out = set()
    for qa in sample["qa"]:
        for raw in qa.get("evidence", []):
            for part in re.split(r"[;,\s]+", str(raw)):
                dia = norm(part) if part else None
                if dia:
                    out.add(f"{conv_id}:{dia}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    samples = {s["sample_id"]: s for s in json.loads(Path(args.source).read_text())}
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for cid in TEST_CONVERSATIONS:
        sample = samples[cid]
        conv = sample["conversation"]
        pub = public_evidence(sample)
        sessions = sorted(int(m.group(1)) for k, v in conv.items()
                          if (m := re.fullmatch(r"session_(\d+)", k)) and isinstance(v, list))
        lines = [f"CONVERSATION {cid} - speakers: {conv['speaker_a']} and {conv['speaker_b']}",
                 "Turns tagged (PUBLIC-EVIDENCE) must NOT be used as evidence.", ""]
        n_turns = 0
        for s in sessions:
            lines.append(f"=== Session {s} - {conv.get(f'session_{s}_date_time', '')} ===")
            for turn in conv[f"session_{s}"]:
                dia = norm(turn["dia_id"]) or turn["dia_id"]
                eid = f"{cid}:{dia}"
                text = f"{turn['speaker']}: {turn['text']}"
                if turn.get("blip_caption"):
                    text += f" [shares image: {turn['blip_caption']}]"
                tag = " (PUBLIC-EVIDENCE)" if eid in pub else ""
                lines.append(f"[{eid}]{tag} {text}")
                n_turns += 1
            lines.append("")
        lines.append("=== Existing PUBLIC questions about this conversation (do not duplicate their facts) ===")
        for qa in sample["qa"]:
            lines.append(f"- {qa['question']}")
        (out_dir / f"{cid}.txt").write_text("\n".join(lines) + "\n")
        (out_dir / f"{cid}.public_evidence.json").write_text(json.dumps(sorted(pub)) + "\n")
        print(cid, "turns", n_turns, "public evidence", len(pub), "public questions", len(sample["qa"]))


if __name__ == "__main__":
    main()
