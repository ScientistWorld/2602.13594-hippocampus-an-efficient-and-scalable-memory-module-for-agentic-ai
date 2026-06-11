#!/usr/bin/env python3
"""HIPPOCAMPUS memory module reproduction.

Implements the paper's core computational steps:
content token-ID stream, semantic binary signatures from sparse random
indexing, append-friendly wavelet matrices with access/rank/select, and
Hamming-ball retrieval followed by exact content reconstruction.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path


TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


class TokenVocabulary:
    def __init__(self) -> None:
        self.token_to_id: dict[str, int] = {"<pad>": 0}
        self.id_to_token: list[str] = ["<pad>"]

    def encode_token(self, token: str) -> int:
        if token not in self.token_to_id:
            self.token_to_id[token] = len(self.id_to_token)
            self.id_to_token.append(token)
        return self.token_to_id[token]

    def encode(self, text: str) -> list[int]:
        return [self.encode_token(tok) for tok in tokenize(text)]

    def decode(self, ids: list[int]) -> str:
        return " ".join(self.id_to_token[i] for i in ids if i < len(self.id_to_token))

    @property
    def bits(self) -> int:
        return max(1, math.ceil(math.log2(max(2, len(self.id_to_token)))))


def _bits_msb(value: int, width: int) -> list[int]:
    return [(value >> shift) & 1 for shift in range(width - 1, -1, -1)]


class DynamicWaveletMatrix:
    """Append-friendly wavelet matrix over integer symbols.

    Each append performs the paper's top-down insertion through bit levels:
    the new symbol is inserted into the current level at the position induced
    by the previous prefix bits, then mapped into the zero/one partition for
    the next level. Rank/select/access use the same transformations described
    in the paper.
    """

    def __init__(self, bit_width: int) -> None:
        self.bit_width = max(1, bit_width)
        self.symbols: list[int] = []
        self.levels: list[list[int]] = [[] for _ in range(self.bit_width)]
        self.zero_counts: list[int] = [0 for _ in range(self.bit_width)]
        self._rank1_prefix: list[list[int]] = [[0] for _ in range(self.bit_width)]
        self._prefix_dirty: list[bool] = [False for _ in range(self.bit_width)]

    @staticmethod
    def _rank1_in_bits(bits: list[int], end: int) -> int:
        end = max(0, min(end, len(bits)))
        return sum(bits[:end])

    @staticmethod
    def _prefix(bits: list[int]) -> list[int]:
        prefix = [0]
        total = 0
        for bit in bits:
            total += bit
            prefix.append(total)
        return prefix

    def append(self, symbol: int) -> None:
        if symbol < 0 or symbol >= (1 << self.bit_width):
            raise ValueError(f"symbol {symbol} does not fit in {self.bit_width} bits")
        pos = len(self.symbols)
        self.symbols.append(symbol)
        for level, bit in enumerate(_bits_msb(symbol, self.bit_width)):
            bits = self.levels[level]
            rank1_before = self._rank1_in_bits(bits, pos)
            rank0_before = pos - rank1_before
            zero_count_before = self.zero_counts[level]
            bits.insert(pos, bit)
            if bit == 0:
                self.zero_counts[level] += 1
                pos = rank0_before
            else:
                pos = zero_count_before + rank1_before
            self._prefix_dirty[level] = True

    def extend(self, symbols: list[int]) -> None:
        for symbol in symbols:
            self.append(symbol)

    def build(self) -> None:
        symbols = list(self.symbols)
        self.symbols = []
        self.levels = [[] for _ in range(self.bit_width)]
        self.zero_counts = [0 for _ in range(self.bit_width)]
        self._rank1_prefix = [[0] for _ in range(self.bit_width)]
        self._prefix_dirty = [False for _ in range(self.bit_width)]
        self.extend(symbols)

    def __len__(self) -> int:
        return len(self.symbols)

    def _ensure_prefix(self, level: int) -> None:
        if self._prefix_dirty[level]:
            self._rank1_prefix[level] = self._prefix(self.levels[level])
            self._prefix_dirty[level] = False

    def rank1(self, level: int, end: int) -> int:
        self._ensure_prefix(level)
        end = max(0, min(end, len(self.symbols)))
        return self._rank1_prefix[level][end]

    def rank0(self, level: int, end: int) -> int:
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
        if index < 0 or index >= len(self.symbols):
            raise IndexError(index)
        pos = index
        value = 0
        for level in range(self.bit_width):
            bit = self.levels[level][pos]
            value = (value << 1) | bit
            if bit == 0:
                pos = self.rank0(level, pos)
            else:
                pos = self.zero_counts[level] + self.rank1(level, pos)
        return value

    def rank(self, symbol: int, end: int) -> int:
        p_l, p_r = 0, max(0, min(end, len(self.symbols)))
        for level, bit in enumerate(_bits_msb(symbol, self.bit_width)):
            if bit == 0:
                p_l = self.rank0(level, p_l)
                p_r = self.rank0(level, p_r)
            else:
                z = self.zero_counts[level]
                p_l = z + self.rank1(level, p_l)
                p_r = z + self.rank1(level, p_r)
        return p_r - p_l

    def select(self, symbol: int, occurrence_1_based: int) -> int | None:
        if occurrence_1_based <= 0:
            return None
        p_l, p_r = 0, len(self.symbols)
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
            bit = bits[level]
            if bit == 0:
                selected = self.select_bit(level, 0, pos + 1)
            else:
                selected = self.select_bit(level, 1, pos - self.zero_counts[level] + 1)
            if selected is None:
                return None
            pos = selected
        return pos

    def approx_bytes(self) -> int:
        for level in range(self.bit_width):
            self._ensure_prefix(level)
        bit_cells = sum(len(level) for level in self.levels)
        rank_cells = sum(len(prefix) for prefix in self._rank1_prefix)
        return math.ceil(bit_cells / 8) + rank_cells * 4 + len(self.zero_counts) * 4


class RandomIndexer:
    def __init__(self, dimension: int = 512, signature_bits: int = 32, sparsity: int = 8, seed: int = 13) -> None:
        self.dimension = dimension
        self.signature_bits = signature_bits
        self.sparsity = sparsity if sparsity % 2 == 0 else sparsity + 1
        self.seed = seed
        self._cache: dict[int, list[tuple[int, int]]] = {}
        self._planes: list[list[tuple[int, int]]] = [self._hyperplane(i) for i in range(signature_bits)]

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

    def _base_vector(self, token_id: int) -> list[tuple[int, int]]:
        if token_id in self._cache:
            return self._cache[token_id]
        pairs: list[tuple[int, int]] = []
        used = set()
        nonce = 0
        while len(pairs) < self.sparsity:
            digest = hashlib.blake2b(f"{self.seed}:{token_id}:{nonce}".encode(), digest_size=8).digest()
            value = int.from_bytes(digest, "little")
            idx = value % self.dimension
            if idx not in used:
                sign = 1 if len(pairs) < self.sparsity // 2 else -1
                pairs.append((idx, sign))
                used.add(idx)
            nonce += 1
        self._cache[token_id] = pairs
        return pairs

    def signatures_for_stream(self, token_ids: list[int], window: int = 2) -> list[int]:
        signatures = []
        for pos in range(len(token_ids)):
            accum = defaultdict(int)
            lo = max(0, pos - window)
            hi = min(len(token_ids), pos + window + 1)
            for neighbor in token_ids[lo:hi]:
                for idx, sign in self._base_vector(neighbor):
                    accum[idx] += sign
            value = 0
            for plane in self._planes:
                dot = sum(accum.get(idx, 0) * sign for idx, sign in plane)
                value = (value << 1) | (1 if dot >= 0 else 0)
            signatures.append(value)
        return signatures


@dataclass
class MemoryEntry:
    entry_id: str
    conversation_id: str
    session: int
    speaker: str
    timestamp: str
    start: int
    end: int
    token_count: int
    text: str


class HippocampusMemory:
    def __init__(self, dimension: int, signature_bits: int, radius: int, window: int, seed: int = 13) -> None:
        self.dimension = dimension
        self.signature_bits = signature_bits
        self.radius = radius
        self.window = window
        self.seed = seed
        self.vocab = TokenVocabulary()
        self.indexer = RandomIndexer(dimension=dimension, signature_bits=signature_bits, seed=seed)
        self.entries: list[MemoryEntry] = []
        self.entry_starts: list[int] = []
        self.content_dwm: DynamicWaveletMatrix | None = None
        self.signature_dwm: DynamicWaveletMatrix | None = None
        self.signature_stream: list[int] = []

    def build(self, conversations: list[dict]) -> None:
        token_stream: list[int] = []
        entry_token_ids: list[list[int]] = []
        metadata: list[MemoryEntry] = []
        for conversation in conversations:
            conv_id = conversation["conversation_id"]
            for raw in conversation["entries"]:
                ids = self.vocab.encode(raw["text"])
                start = len(token_stream)
                token_stream.extend(ids)
                end = len(token_stream)
                metadata.append(
                    MemoryEntry(
                        entry_id=raw["entry_id"],
                        conversation_id=conv_id,
                        session=raw["session"],
                        speaker=raw["speaker"],
                        timestamp=raw["timestamp"],
                        start=start,
                        end=end,
                        token_count=len(ids),
                        text=raw["text"],
                    )
                )
                entry_token_ids.append(ids)

        self.entries = metadata
        self.entry_starts = [entry.start for entry in self.entries]
        self.content_dwm = DynamicWaveletMatrix(max(self.vocab.bits, 1))
        self.content_dwm.extend(token_stream)
        self.content_dwm.build()

        signatures: list[int] = []
        for ids in entry_token_ids:
            signatures.extend(self.indexer.signatures_for_stream(ids, window=self.window))
        self.signature_stream = signatures
        self.signature_dwm = DynamicWaveletMatrix(self.signature_bits)
        self.signature_dwm.extend(signatures)
        self.signature_dwm.build()

    def _entry_for_position(self, pos: int) -> MemoryEntry:
        idx = bisect.bisect_right(self.entry_starts, pos) - 1
        return self.entries[max(0, idx)]

    def _query_signatures(self, question: str) -> list[int]:
        ids = [self.vocab.encode_token(tok) for tok in tokenize(question)]
        stop = {"which", "what", "did", "for", "the", "at", "on", "use", "used", "by", "should", "be"}
        keyword_ids = [self.vocab.token_to_id[tok] for tok in tokenize(question) if tok not in stop]
        if not keyword_ids:
            keyword_ids = ids
        return self.indexer.signatures_for_stream(keyword_ids, window=1)

    @staticmethod
    def _ham(a: int, b: int) -> int:
        return (a ^ b).bit_count()

    def retrieve(self, question: str, top_k: int = 3, conversation_id: str | None = None) -> dict:
        if self.signature_dwm is None or self.content_dwm is None:
            raise RuntimeError("memory not built")
        start_time = time.perf_counter()
        query_signatures = self._query_signatures(question)
        scores: Counter[str] = Counter()
        first_positions: dict[str, int] = {}
        comparisons = 0
        for pos in range(len(self.signature_dwm)):
            stored = self.signature_dwm.access(pos)
            entry = self._entry_for_position(pos)
            if conversation_id is not None and entry.conversation_id != conversation_id:
                continue
            min_distance = min(self._ham(sig, stored) for sig in query_signatures)
            comparisons += len(query_signatures)
            if min_distance <= self.radius:
                scores[entry.entry_id] += self.radius - min_distance + 1
                first_positions.setdefault(entry.entry_id, pos)

        if not scores:
            # Fallback preserves usability when the Hamming radius is too tight.
            for pos in range(len(self.signature_dwm)):
                stored = self.signature_dwm.access(pos)
                entry = self._entry_for_position(pos)
                if conversation_id is not None and entry.conversation_id != conversation_id:
                    continue
                min_distance = min(self._ham(sig, stored) for sig in query_signatures)
                scores[entry.entry_id] += max(1, self.signature_bits - min_distance)
                first_positions.setdefault(entry.entry_id, pos)

        entry_by_id = {entry.entry_id: entry for entry in self.entries}
        # Metadata-span validation from the paper: use Signature-DWM rank to
        # check whether query signatures co-occur inside candidate spans.
        for entry_id in list(scores):
            entry = entry_by_id[entry_id]
            signature_hits = 0
            for signature in query_signatures:
                signature_hits += int(
                    self.signature_dwm.rank(signature, entry.end) - self.signature_dwm.rank(signature, entry.start) > 0
                )
            scores[entry_id] += signature_hits * (self.radius + 2)

        ranked_entries = sorted(
            (entry_by_id[entry_id] for entry_id in scores),
            key=lambda entry: (-scores[entry.entry_id], entry.session, entry.entry_id),
        )[:top_k]
        retrieved = []
        token_footprint = 0
        for entry in ranked_entries:
            ids = [self.content_dwm.access(i) for i in range(entry.start, entry.end)]
            token_footprint += len(ids)
            retrieved.append({**asdict(entry), "reconstructed_text": self.vocab.decode(ids), "score": scores[entry.entry_id]})
        elapsed = time.perf_counter() - start_time
        return {
            "retrieved": retrieved,
            "search_time_s": elapsed,
            "signature_comparisons": comparisons,
            "bit_operations": comparisons * math.ceil(self.signature_bits / 64),
            "token_footprint": token_footprint,
            "storage_bytes": (self.content_dwm.approx_bytes() + self.signature_dwm.approx_bytes()),
        }


def run(args: argparse.Namespace) -> None:
    dataset = json.loads(Path(args.data).read_text())
    memory = HippocampusMemory(
        dimension=args.dimension,
        signature_bits=args.signature_bits,
        radius=args.radius,
        window=args.window,
        seed=args.seed,
    )
    memory.build(dataset["conversations"])

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "retrieval_results.jsonl").open("w") as f:
        for item in dataset["questions"]:
            result = memory.retrieve(item["question"], top_k=args.top_k, conversation_id=item["conversation_id"])
            row = {
                "method": args.method_name,
                "question_id": item["question_id"],
                "conversation_id": item["conversation_id"],
                "question": item["question"],
                "answer": item["answer"],
                "gold_entry_ids": item["gold_entry_ids"],
                **result,
            }
            f.write(json.dumps(row) + "\n")
    config = vars(args) | {
        "vocab_size": len(memory.vocab.id_to_token),
        "entries": len(memory.entries),
        "tokens": len(memory.content_dwm) if memory.content_dwm else 0,
    }
    (output_dir / "config.json").write_text(json.dumps(config, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/memory_qa.json")
    parser.add_argument("--output-dir", default="outputs/hippocampus")
    parser.add_argument("--dimension", type=int, default=512)
    parser.add_argument("--signature-bits", type=int, default=32)
    parser.add_argument("--radius", type=int, default=9)
    parser.add_argument("--window", type=int, default=2)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--method-name", default="hippocampus")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
