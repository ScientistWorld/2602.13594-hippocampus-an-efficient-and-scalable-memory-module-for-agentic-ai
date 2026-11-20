# Overview

The paper proposes HIPPOCAMPUS, a memory substrate for agentic AI. It replaces dense vector databases and knowledge graphs with compact binary token signatures for search and a lossless token-ID stream for exact content reconstruction, both indexed by Dynamic Wavelet Matrices. Its claim is that retrieval quality is preserved while search latency and per-query token footprint drop sharply (evaluated on LoCoMo and LongMemEval).

This gym measures that trade-off on LoCoMo turn-level evidence retrieval. Each method returns at most 10 dialogue turns per question. It is scored on how much labelled evidence it recovers and how much context it delivers. The test conversations are held out, their questions are private, and the evaluator runs each method on them.
