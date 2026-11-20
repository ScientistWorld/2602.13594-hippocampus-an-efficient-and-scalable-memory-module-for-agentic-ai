#!/usr/bin/env python3
"""Audit variant (not part of the gym): BM25 with light stemming and adjacent-turn context.

Used only to check that the hidden test rewards gains beyond the exhaustive
BM25 baseline. Each turn's document is its own text plus, at a lower weight,
the text of the turn just before it (replies often omit the topic words of the
question they answer). Terms are reduced with a tiny suffix stemmer.
    python redteam/hardening/better_bm25_context.py --input <memory.json> --output <results.jsonl>
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
STOPWORDS = frozenset(
    """
    a about above after again against all am an and any are as at be because been before being below
    between both but by can could did do does doing done down during each few for from further get got
    had has have having he her here hers herself him himself his how i if in into is it its itself just
    me more most my myself no nor not now of off on once only or other our ours ourselves out over own
    same she should so some such than that the their theirs them themselves then there these they this
    those through to too under until up very was we were what when where which while who whom why will
    with would you your yours yourself yourselves s t don ever also many much kind kinds type types
    like likely
    """.split()
)


def stem(tok: str) -> str:
    tok = tok.split("'")[0]
    for suffix in ("ing", "ed", "es", "s", "ly"):
        if tok.endswith(suffix) and len(tok) - len(suffix) >= 3:
            tok = tok[: -len(suffix)]
            break
    if len(tok) > 3 and tok[-1] == tok[-2] and tok[-1] not in "aeiouls":
        tok = tok[:-1]
    return tok


def terms(text: str) -> list[str]:
    return [stem(t) for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


class Index:
    def __init__(self, entries: list[dict], context_weight: float = 0.4, k1: float = 1.2, b: float = 0.75) -> None:
        self.ids = [e["entry_id"] for e in entries]
        own = [Counter(terms(e["text"])) for e in entries]
        self.docs = []
        for i, tf in enumerate(own):
            doc = Counter({t: float(c) for t, c in tf.items()})
            if i > 0 and entries[i - 1]["session"] == entries[i]["session"]:
                for t, c in own[i - 1].items():
                    doc[t] += context_weight * c
            self.docs.append(doc)
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.lengths) / max(1, len(self.lengths))
        df = Counter()
        for d in own:
            df.update(d.keys())
        n = len(entries)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self.k1, self.b = k1, b

    def search(self, question: str, top_k: int) -> list[str]:
        q = sorted(set(terms(question)))
        scored = []
        for i, doc in enumerate(self.docs):
            norm = self.k1 * (1 - self.b + self.b * self.lengths[i] / self.avg)
            s = 0.0
            for t in q:
                f = doc.get(t)
                if f:
                    s += self.idf.get(t, 0.0) * f * (self.k1 + 1) / (f + norm)
            scored.append((-s, i))
        scored.sort()
        return [self.ids[i] for _, i in scored[:top_k]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--context-weight", type=float, default=0.4)
    args = ap.parse_args()
    data = json.loads(Path(args.input).read_text())
    idx = {c["conversation_id"]: Index(c["entries"], args.context_weight) for c in data["conversations"]}
    with Path(args.output).open("w") as out:
        for q in data["questions"]:
            ids = idx[q["conversation_id"]].search(q["question"], args.top_k)
            out.write(json.dumps({"question_id": q["question_id"], "retrieved_entry_ids": ids}) + "\n")


if __name__ == "__main__":
    main()
