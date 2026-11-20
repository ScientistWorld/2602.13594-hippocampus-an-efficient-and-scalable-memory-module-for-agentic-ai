# Experiment Overview

## locomo_memory_retrieval

Tests the central memory claim: over very long multi-session conversations, a memory system should recall the dialogue turns needed to answer a question while delivering only a small amount of context per question. It is measured on held-out LoCoMo conversations the method has never seen, with private questions written for them in LoCoMo's style. These are not the public LoCoMo questions.

Quality is measured by how much of each question's labelled evidence appears among at most 10 returned turns. Supporting measures are whether the top-ranked turn is evidence, whether the answer's words reach the delivered context, and the weakest of the four question groups (single-hop, multi-hop, temporal, open-domain). Cost is the number of context tokens delivered per question.

Scoring both sides keeps a method from winning by delivering more context, or by delivering less context while losing the evidence. Runs that break the output contract, or recover almost no evidence, are scored as failed.
