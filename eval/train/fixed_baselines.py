"""Evaluator-owned comparison procedures. No imports from method or baseline.
Frozen Okapi BM25 (k1=1.2, b=.75), recency, and full-history context cost.
Duplicated between splits so neither split imports the other.
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


def tokenize(text: str) -> list[str]:
    return [tok for tok in TOKEN_RE.findall(text.lower()) if tok not in STOPWORDS]


class BM25Index:
    def __init__(self, entries: list[dict], k1: float = 1.2, b: float = 0.75) -> None:
        self.ids = [entry["entry_id"] for entry in entries]
        self.order = [(entry["session"], entry["turn"]) for entry in entries]
        self.tfs = [Counter(tokenize(entry["text"])) for entry in entries]
        self.lengths = [sum(tf.values()) for tf in self.tfs]
        self.avg_len = sum(self.lengths) / max(1, len(self.lengths))
        df = Counter()
        for tf in self.tfs:
            df.update(tf.keys())
        n = len(entries)
        self.idf = {tok: math.log(1 + (n - count + 0.5) / (count + 0.5)) for tok, count in df.items()}
        self.k1, self.b = k1, b

    def search(self, question: str, top_k: int) -> list[str]:
        terms = sorted(set(tokenize(question)))
        scored = []
        for index, tf in enumerate(self.tfs):
            norm = self.k1 * (1 - self.b + self.b * self.lengths[index] / self.avg_len)
            score = 0.0
            for term in terms:
                freq = tf.get(term)
                if freq:
                    score += self.idf[term] * freq * (self.k1 + 1) / (freq + norm)
            scored.append((-score, self.order[index], index))
        scored.sort()
        return [self.ids[index] for _, _, index in scored[:top_k]]



def rankings(data: dict, budget: int) -> dict:
    indexes = {c["conversation_id"]: BM25Index(c["entries"]) for c in data["conversations"]}
    latest = {
        c["conversation_id"]: [e["entry_id"] for e in sorted(
            c["entries"], key=lambda e: (e["session"], e["turn"]), reverse=True)[:budget]]
        for c in data["conversations"]
    }
    return {
        "bm25": {q["question_id"]: indexes[q["conversation_id"]].search(q["question"], budget)
                 for q in data["questions"]},
        "recency": {q["question_id"]: latest[q["conversation_id"]] for q in data["questions"]},
    }
