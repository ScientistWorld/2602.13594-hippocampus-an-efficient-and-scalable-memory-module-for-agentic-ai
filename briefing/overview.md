# Overview

The paper proposes HIPPOCAMPUS, an efficient memory substrate for agentic AI. Instead of dense vector databases or knowledge graphs, it uses compact binary token signatures for semantic search and a lossless token-ID stream for exact content reconstruction. Both streams are indexed by Dynamic Wavelet Matrices.

The central claim is that this compressed-domain memory can preserve retrieval quality while reducing search latency and retrieved-token cost. This workspace reproduces the core mechanism on a portable long-memory QA benchmark and scores both accuracy and efficiency constraints.
