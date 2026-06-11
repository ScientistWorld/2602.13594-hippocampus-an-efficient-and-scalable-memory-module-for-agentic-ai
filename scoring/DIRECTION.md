# Research Direction

## Research Problem
Improve long-term contextual memory retrieval for agentic systems. The goal is to recall relevant past entries from growing conversational histories without relying on large prompt contexts or expensive dense-vector search.

## Core Contribution
The paper contributes a compressed memory substrate with binary semantic signatures and exact content reconstruction. Improvements should stay within the problem of efficient external memory indexing and retrieval.

## Approach Scope
In-bounds work may improve signature generation, compressed indexing, candidate validation, metadata use, or ranking while preserving the goal of compact memory retrieval. Alternative succinct indexes, better binary hashing, and improved span validation are all within scope.

## Out of Bounds
Do not replace the task with answer generation from a large LLM context, full-history prompting, or a large neural retriever whose gains mainly come from pretrained model scale. Do not add external labeled data to the scoring set.
