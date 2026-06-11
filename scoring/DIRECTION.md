# Research Direction

## Research Problem
Improve long-term contextual memory retrieval for agentic systems. The goal is to recall relevant past entries from growing conversational histories without relying on large prompt contexts or expensive dense-vector search.

## Core Contribution
The paper contributes an efficient external memory substrate for selective recall under context-budget and search-work constraints. Improvements should stay within the problem of compact long-memory indexing and retrieval.

## Approach Scope
In-bounds work may improve compact representations, indexing, candidate validation, metadata use, or ranking while preserving the goal of selective memory retrieval with a small returned context.

## Out of Bounds
Do not replace the task with answer generation from a large LLM context, full-history prompting, or a large neural retriever whose gains mainly come from pretrained model scale. Do not add external labeled data to the scoring set.
