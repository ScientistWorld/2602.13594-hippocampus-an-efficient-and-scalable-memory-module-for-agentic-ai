# Problem

Agentic AI systems need persistent contextual memory: past dialogue turns, tool outputs, and user-specific facts must be stored outside the LLM context window and retrieved later when a user asks a related question.

The task in this workspace is long-memory retrieval. Given a multi-session conversation history and a natural-language question, a memory system must return a small set of stored memory entries that contain the answer. The answer-bearing entries are labeled in `data/memory_qa.json`.

A successful system should retrieve the correct entries while keeping the per-query retrieved-token footprint and search work low. The benchmark is intentionally method-agnostic: any system may write retrieval artifacts in the expected JSONL format and run `scripts/evaluate.sh`.
