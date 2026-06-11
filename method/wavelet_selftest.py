#!/usr/bin/env python3
"""Self-test for HIPPOCAMPUS DynamicWaveletMatrix primitives."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from method.hippocampus import DynamicWaveletMatrix


def main() -> None:
    sequence = [5, 1, 7, 5, 0, 3, 5, 2, 7, 1, 4, 6, 0, 5]
    matrix = DynamicWaveletMatrix(bit_width=3)
    for symbol in sequence:
        matrix.append(symbol)

    reconstructed = [matrix.access(i) for i in range(len(sequence))]
    assert reconstructed == sequence, (reconstructed, sequence)

    for symbol in range(8):
        positions = [i for i, value in enumerate(sequence) if value == symbol]
        for end in range(len(sequence) + 1):
            assert matrix.rank(symbol, end) == sequence[:end].count(symbol)
        for occurrence, expected_position in enumerate(positions, start=1):
            assert matrix.select(symbol, occurrence) == expected_position
        assert matrix.select(symbol, len(positions) + 1) is None

    print("DynamicWaveletMatrix self-test passed")


if __name__ == "__main__":
    main()
