#!/usr/bin/env python3
"""HIPPOCAMPUS memory module reproduction (Li et al., 2026).

Implements the paper's computational steps for each agent memory
(one LoCoMo conversation):

1. Content serialisation: every memory entry (dialogue turn) is tokenised into
   token IDs and appended to a Content Dynamic Wavelet Matrix (DWM); entry
   metadata keeps the start/end token offsets (alpha, beta).
2. Random indexing: every token gets a fixed sparse ternary base vector in a
   D-dimensional space; a token's contextual embedding is the sum of base
   vectors over a sliding window. Each embedding is hashed to a d-bit binary
   signature with sign-of-random-hyperplane bits (the paper's Appendix G
   formulation). Signatures are appended to a Signature DWM.
3. Query: salient query keywords are hashed with the same random-indexing
   module, the stored signature stream (decoded from the Signature DWM) is
   scanned with XOR + popcount, and positions inside the Hamming ball of radius
   r are mapped back to their memory entries through the metadata.
4. Metadata validation: candidate entries are ranked by how many query
   keywords co-occur inside their span; exact signature co-occurrence is
   verified with Signature-DWM rank(c, beta) - rank(c, alpha) > 0, and the
   least frequent query signature is found with rank(c, n).
5. Reconstruction: the selected entries are rebuilt losslessly from the
   Content DWM with access(i) over [alpha, beta).

I/O contract (shared by every retriever in this gym):
    python method/hippocampus.py --input <memory.json> --output <results.jsonl>
The input holds conversations (entries) and label-free questions; each output
row is {"question_id": ..., "retrieved_entry_ids": [ranked ids]}.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
import random
import re
from collections import defaultdict
from dataclasses import dataclass
from itertools import accumulate
from pathlib import Path


TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")

# Stand-in for the paper's lightweight LLM keyword-extraction prompt: drop
# function words and keep the content words of the question.
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
    return TOKEN_RE.findall(text.lower())


def keywords(question: str) -> list[str]:
    tokens = tokenize(question)
    kept = [tok for tok in tokens if tok not in STOPWORDS]
    return kept or tokens


class TokenVocabulary:
    def __init__(self) -> None:
        self.token_to_id: dict[str, int] = {"<pad>": 0}
        self.id_to_token: list[str] = ["<pad>"]

    def encode_token(self, token: str) -> int:
        if token not in self.token_to_id:
            self.token_to_id[token] = len(self.id_to_token)
            self.id_to_token.append(token)
        return self.token_to_id[token]

    def decode(self, ids: list[int]) -> str:
        return " ".join(self.id_to_token[i] for i in ids)

    @property
    def bits(self) -> int:
        return max(1, math.ceil(math.log2(max(2, len(self.id_to_token)))))


def _bits_msb(value: int, width: int) -> list[int]:
    return [(value >> shift) & 1 for shift in range(width - 1, -1, -1)]


class DynamicWaveletMatrix:
    """Append-only wavelet matrix over integer symbols (paper Section 3.2).

    Each level is a bit-vector B^k. append(s) performs the paper's single
    top-down traversal: the k-th bit of s is inserted into B^k at the position
    induced by the previous levels (rank_0 into the zero block, Z_k + rank_1
    into the one block). No copy of the raw symbol sequence is kept; access,
    rank and select read only the level bit-vectors and zero counts.
    """

    def __init__(self, bit_width: int) -> None:
        self.bit_width = max(1, bit_width)
        self.length = 0
        self.levels: list[bytearray] = [bytearray() for _ in range(self.bit_width)]
        self.zero_counts: list[int] = [0] * self.bit_width
        self._rank1_prefix: list[list[int] | None] = [None] * self.bit_width

    def append(self, symbol: int) -> None:
        if symbol < 0 or symbol >= (1 << self.bit_width):
            raise ValueError(f"symbol {symbol} does not fit in {self.bit_width} bits")
        pos = self.length
        for level, bit in enumerate(_bits_msb(symbol, self.bit_width)):
            bits = self.levels[level]
            rank1_before = bits.count(1, 0, pos)
            zero_count_before = self.zero_counts[level]
            bits.insert(pos, bit)
            self._rank1_prefix[level] = None
            if bit == 0:
                self.zero_counts[level] += 1
                pos = pos - rank1_before
            else:
                pos = zero_count_before + rank1_before
        self.length += 1

    def extend(self, symbols: list[int]) -> None:
        for symbol in symbols:
            self.append(symbol)

    def __len__(self) -> int:
        return self.length

    def _prefix(self, level: int) -> list[int]:
        prefix = self._rank1_prefix[level]
        if prefix is None:
            prefix = [0]
            prefix.extend(accumulate(self.levels[level]))
            self._rank1_prefix[level] = prefix
        return prefix

    def rank1(self, level: int, end: int) -> int:
        return self._prefix(level)[max(0, min(end, self.length))]

    def rank0(self, level: int, end: int) -> int:
        end = max(0, min(end, self.length))
        return end - self.rank1(level, end)

    def select_bit(self, level: int, bit: int, occurrence_1_based: int) -> int | None:
        if occurrence_1_based <= 0:
            return None
        count = 0
        for idx, value in enumerate(self.levels[level]):
            if value == bit:
                count += 1
                if count == occurrence_1_based:
                    return idx
        return None

    def access(self, index: int) -> int:
        """Algorithm 3: read one bit per level, following rank mappings."""
        if index < 0 or index >= self.length:
            raise IndexError(index)
        pos = index
        value = 0
        for level in range(self.bit_width):
            bit = self.levels[level][pos]
            value = (value << 1) | bit
            prefix = self._prefix(level)
            if bit == 0:
                pos = pos - prefix[pos]
            else:
                pos = self.zero_counts[level] + prefix[pos]
        return value

    def rank(self, symbol: int, end: int) -> int:
        """Algorithm 1: number of occurrences of symbol in S[0, end)."""
        p_l, p_r = 0, max(0, min(end, self.length))
        for level, bit in enumerate(_bits_msb(symbol, self.bit_width)):
            prefix = self._prefix(level)
            if bit == 0:
                p_l = p_l - prefix[p_l]
                p_r = p_r - prefix[p_r]
            else:
                z = self.zero_counts[level]
                p_l = z + prefix[p_l]
                p_r = z + prefix[p_r]
            if p_l == p_r:
                return 0
        return p_r - p_l

    def select(self, symbol: int, occurrence_1_based: int) -> int | None:
        """Algorithm 2: global position of the j-th occurrence of symbol."""
        if occurrence_1_based <= 0:
            return None
        p_l, p_r = 0, self.length
        bits = _bits_msb(symbol, self.bit_width)
        for level, bit in enumerate(bits):
            if bit == 0:
                p_l = self.rank0(level, p_l)
                p_r = self.rank0(level, p_r)
            else:
                z = self.zero_counts[level]
                p_l = z + self.rank1(level, p_l)
                p_r = z + self.rank1(level, p_r)
        if occurrence_1_based > p_r - p_l:
            return None
        pos = p_l + occurrence_1_based - 1
        for level in range(self.bit_width - 1, -1, -1):
            if bits[level] == 0:
                selected = self.select_bit(level, 0, pos + 1)
            else:
                selected = self.select_bit(level, 1, pos - self.zero_counts[level] + 1)
            if selected is None:
                return None
            pos = selected
        return pos

    def approx_bytes(self) -> int:
        return math.ceil(sum(len(level) for level in self.levels) / 8) + 4 * self.bit_width


class RandomIndexer:
    """Sparse random indexing + random-hyperplane binarisation.

    Each token v has a fixed sparse ternary base vector r_v in {-1,0,+1}^D with
    `sparsity` non-zeros (half +1, half -1). The contextual embedding of the
    token at position i is e_i = sum_{j in W(i)} r_{S[j]}. Signature bit k is
    1 iff <h_k, e_i> >= 0 for a fixed sparse random hyperplane h_k. Because
    <h_k, e_i> = sum_j <h_k, r_{S[j]}>, the per-token projections are cached
    and summed over the window, which is exactly the same computation.
    """

    def __init__(
        self,
        dimension: int = 512,
        signature_bits: int = 32,
        sparsity: int = 8,
        seed: int = 13,
        hyperplanes: str = "dense",
    ) -> None:
        self.dimension = dimension
        self.signature_bits = signature_bits
        self.sparsity = sparsity if sparsity % 2 == 0 else sparsity + 1
        self.seed = seed
        self.hyperplanes = hyperplanes
        if hyperplanes == "dense":
            # Appendix G: independent Gaussian hyperplanes h_k ~ N(0, I_D).
            rng = random.Random(f"planes:{seed}:{dimension}")
            self._planes = [
                {idx: rng.gauss(0.0, 1.0) for idx in range(dimension)} for _ in range(signature_bits)
            ]
        else:
            # Very sparse +-1 hyperplanes (16 non-zeros); kept as an ablation.
            self._planes = [dict(self._hyperplane(i)) for i in range(signature_bits)]
        self._projection_cache: dict[str, tuple[float, ...]] = {}

    def _hyperplane(self, plane_id: int) -> list[tuple[int, int]]:
        pairs: list[tuple[int, int]] = []
        used = set()
        nonce = 0
        plane_sparsity = min(self.dimension, max(16, self.sparsity * 2))
        while len(pairs) < plane_sparsity:
            digest = hashlib.blake2b(f"plane:{self.seed}:{plane_id}:{nonce}".encode(), digest_size=8).digest()
            value = int.from_bytes(digest, "little")
            idx = value % self.dimension
            if idx not in used:
                sign = 1 if ((value >> 17) & 1) else -1
                pairs.append((idx, sign))
                used.add(idx)
            nonce += 1
        return pairs

    def base_vector(self, token: str) -> list[tuple[int, int]]:
        pairs: list[tuple[int, int]] = []
        used = set()
        nonce = 0
        while len(pairs) < self.sparsity:
            digest = hashlib.blake2b(f"{self.seed}:{token}:{nonce}".encode(), digest_size=8).digest()
            value = int.from_bytes(digest, "little")
            idx = value % self.dimension
            if idx not in used:
                sign = 1 if len(pairs) < self.sparsity // 2 else -1
                pairs.append((idx, sign))
                used.add(idx)
            nonce += 1
        return pairs

    def _projection(self, token: str) -> tuple[float, ...]:
        cached = self._projection_cache.get(token)
        if cached is None:
            base = self.base_vector(token)
            cached = tuple(sum(plane.get(idx, 0) * sign for idx, sign in base) for plane in self._planes)
            self._projection_cache[token] = cached
        return cached

    def signatures_for_stream(self, tokens: list[str], window: int = 2) -> list[int]:
        projections = [self._projection(tok) for tok in tokens]
        signatures = []
        n_bits = self.signature_bits
        for pos in range(len(tokens)):
            lo = max(0, pos - window)
            hi = min(len(tokens), pos + window + 1)
            totals = [0.0] * n_bits
            for proj in projections[lo:hi]:
                for k in range(n_bits):
                    totals[k] += proj[k]
            value = 0
            for total in totals:
                value = (value << 1) | (1 if total >= 0 else 0)
            signatures.append(value)
        return signatures


@dataclass
class MemoryEntry:
    entry_id: str
    session: int
    turn: int
    speaker: str
    date_time: str
    start: int
    end: int


class HippocampusMemory:
    """One agent memory: a Content DWM and a Signature DWM co-indexed by offsets."""

    def __init__(
        self,
        dimension: int = 512,
        signature_bits: int = 32,
        radius: int = 8,
        window: int = 1,
        query_window: int = 0,
        seed: int = 13,
        scoring: str = "cooccurrence",
        keyword_weighting: str = "uniform",
        hyperplanes: str = "dense",
    ) -> None:
        self.dimension = dimension
        self.signature_bits = signature_bits
        self.radius = radius
        self.window = window
        self.query_window = query_window
        self.seed = seed
        self.scoring = scoring
        self.keyword_weighting = keyword_weighting
        self.vocab = TokenVocabulary()
        self.indexer = RandomIndexer(
            dimension=dimension, signature_bits=signature_bits, seed=seed, hyperplanes=hyperplanes
        )
        self.entries: list[MemoryEntry] = []
        self.entry_starts: list[int] = []
        self.content_dwm = DynamicWaveletMatrix(1)
        self.signature_dwm = DynamicWaveletMatrix(signature_bits)
        self._scan_signatures: list[int] = []
        self._position_entry: list[int] = []

    def build(self, entries: list[dict]) -> None:
        token_stream: list[int] = []
        signature_stream: list[int] = []
        for raw in entries:
            tokens = tokenize(raw["text"])
            ids = [self.vocab.encode_token(tok) for tok in tokens]
            start = len(token_stream)
            token_stream.extend(ids)
            signature_stream.extend(self.indexer.signatures_for_stream(tokens, window=self.window))
            self.entries.append(
                MemoryEntry(
                    entry_id=raw["entry_id"],
                    session=int(raw.get("session", 0)),
                    turn=int(raw.get("turn", 0)),
                    speaker=str(raw.get("speaker", "")),
                    date_time=str(raw.get("date_time", "")),
                    start=start,
                    end=len(token_stream),
                )
            )
        self.entry_starts = [entry.start for entry in self.entries]
        self.content_dwm = DynamicWaveletMatrix(self.vocab.bits)
        self.content_dwm.extend(token_stream)
        self.signature_dwm = DynamicWaveletMatrix(self.signature_bits)
        self.signature_dwm.extend(signature_stream)
        # The Hamming scan reads stored signatures out of the Signature DWM
        # (access(i) for every position); decode once per memory.
        self._scan_signatures = [self.signature_dwm.access(i) for i in range(len(self.signature_dwm))]
        if self._scan_signatures != signature_stream:
            raise RuntimeError("Signature DWM failed lossless reconstruction")
        self._position_entry = []
        for index, entry in enumerate(self.entries):
            self._position_entry.extend([index] * (entry.end - entry.start))

    def entry_for_position(self, pos: int) -> MemoryEntry:
        return self.entries[max(0, bisect.bisect_right(self.entry_starts, pos) - 1)]

    def reconstruct(self, entry: MemoryEntry) -> str:
        return self.vocab.decode([self.content_dwm.access(i) for i in range(entry.start, entry.end)])

    def retrieve(self, question: str, top_k: int = 10) -> dict:
        query_tokens = keywords(question)
        query_signatures = self.indexer.signatures_for_stream(query_tokens, window=self.query_window)
        n_query = len(query_signatures)
        radius = self.radius
        # best[e][q] = best in-ball closeness (radius - distance + 1) of keyword q in entry e
        best: dict[int, list[int]] = defaultdict(lambda: [0] * n_query)
        position_score: dict[int, int] = defaultdict(int)
        comparisons = 0
        position_entry = self._position_entry
        for pos, stored in enumerate(self._scan_signatures):
            comparisons += n_query
            entry_index = -1
            for q, signature in enumerate(query_signatures):
                distance = (signature ^ stored).bit_count()
                if distance <= radius:
                    closeness = radius - distance + 1
                    if entry_index < 0:
                        entry_index = position_entry[pos]
                    row = best[entry_index]
                    if closeness > row[q]:
                        row[q] = closeness
                    position_score[entry_index] += closeness

        n_entries = len(self.entries)
        weights = [1.0] * n_query
        if self.keyword_weighting == "idf":
            for q in range(n_query):
                df = sum(1 for row in best.values() if row[q] > 0)
                weights[q] = math.log((n_entries + 1) / (df + 0.5))

        # Metadata validation with Signature-DWM rank: exact co-occurrence of
        # query signatures inside an entry span. rank(c, n) gives each query
        # signature's frequency; signatures absent from memory are skipped.
        present = [q for q, sig in enumerate(query_signatures) if self.signature_dwm.rank(sig, len(self.signature_dwm)) > 0]
        present.sort(key=lambda q: self.signature_dwm.rank(query_signatures[q], len(self.signature_dwm)))

        scores: dict[int, float] = {}
        for entry_index, row in best.items():
            entry = self.entries[entry_index]
            exact = 0
            for q in present:
                sig = query_signatures[q]
                if self.signature_dwm.rank(sig, entry.end) - self.signature_dwm.rank(sig, entry.start) > 0:
                    exact += 1
            if self.scoring == "position_sum":
                scores[entry_index] = position_score[entry_index] + exact * (radius + 2)
            else:
                matched = sum(weights[q] for q in range(n_query) if row[q] > 0)
                closeness = sum(weights[q] * row[q] for q in range(n_query)) / (radius + 1)
                scores[entry_index] = (radius + 2) * matched + closeness + exact * (radius + 2)

        if not scores:
            # Fallback when the Hamming ball is empty: nearest signatures.
            for pos, stored in enumerate(self._scan_signatures):
                distance = min((sig ^ stored).bit_count() for sig in query_signatures) if query_signatures else 0
                entry_index = position_entry[pos]
                scores[entry_index] = max(scores.get(entry_index, 0.0), float(self.signature_bits - distance))

        ranked = sorted(scores, key=lambda idx: (-scores[idx], self.entries[idx].session, self.entries[idx].turn))[:top_k]
        retrieved = [self.entries[idx] for idx in ranked]
        # Exact, lossless reconstruction of each returned entry from the Content DWM.
        content = [self.reconstruct(entry) for entry in retrieved]
        return {
            "retrieved_entry_ids": [entry.entry_id for entry in retrieved],
            "retrieved_content": content,
            "diagnostics": {
                "query_keywords": query_tokens,
                "signature_comparisons": comparisons,
                "candidate_entries": len(best),
                "reconstructed_tokens": sum(entry.end - entry.start for entry in retrieved),
            },
        }


def run(args: argparse.Namespace) -> None:
    dataset = json.loads(Path(args.input).read_text())
    memories: dict[str, HippocampusMemory] = {}
    for conversation in dataset["conversations"]:
        memory = HippocampusMemory(
            dimension=args.dimension,
            signature_bits=args.signature_bits,
            radius=args.radius,
            window=args.window,
            query_window=args.query_window,
            seed=args.seed,
            scoring=args.scoring,
            keyword_weighting=args.keyword_weighting,
            hyperplanes=args.hyperplanes,
        )
        memory.build(conversation["entries"])
        memories[conversation["conversation_id"]] = memory

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w") as handle:
        for item in dataset["questions"]:
            memory = memories[item["conversation_id"]]
            result = memory.retrieve(item["question"], top_k=args.top_k)
            handle.write(json.dumps({"question_id": item["question_id"], **result}) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--input", required=True, help="memory/question JSON (labels are ignored)")
    parser.add_argument("--output", required=True, help="retrieval results JSONL")
    parser.add_argument("--dimension", type=int, default=512)
    parser.add_argument("--signature-bits", type=int, default=32)
    parser.add_argument("--radius", type=int, default=8)
    parser.add_argument("--window", type=int, default=1)
    parser.add_argument("--query-window", type=int, default=0)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--scoring", choices=["cooccurrence", "position_sum"], default="cooccurrence")
    parser.add_argument("--keyword-weighting", choices=["uniform", "idf"], default="uniform")
    parser.add_argument("--hyperplanes", choices=["dense", "sparse"], default="dense")
    return parser


def main() -> None:
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
