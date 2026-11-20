# Research Direction

## Research Problem
Improve long-term conversational memory recall for agentic systems: find the few past dialogue turns that answer a new question in a history of hundreds of turns, while delivering little context.

## Core Contribution
The paper contributes a lightweight memory substrate that indexes conversation history compactly. It aims to keep recall quality while making search cheap and the returned context small.

## Approach Scope
In bounds: better compact representations of memory entries, keyword or query processing, candidate generation and validation, ranking, use of metadata (speakers, sessions, timestamps), and choosing how many entries to return.

## Where the reference falls short
On LoCoMo the reference recovers about a quarter of the evidence turns. Open-domain and multi-hop questions are hardest. It prefers long turns, so it delivers more context than needed. Exhaustive lexical scoring already recovers more than twice as much evidence, so there is substantial headroom.

## Out of Bounds
Full-history prompting, answer generation with large LLMs, large pretrained neural retrievers, external labelled data, or any use of the held-out labels.
