# Method (reference implementation in `method/hippocampus.py`)

HIPPOCAMPUS keeps one memory per conversation, made of two co-indexed Dynamic Wavelet Matrices (DWMs):

- **Content DWM:** each entry's text is tokenised into token IDs and appended symbol by symbol. Each append is the paper's top-down traversal: insert one bit per level at the position induced by rank_0/rank_1 of the previous level. Entry metadata stores the start/end offsets (alpha, beta). Entries are rebuilt losslessly with `access(i)`.
- **Signature DWM:** every token gets a fixed sparse ternary random-index vector (D = 512, 8 non-zeros). A token's contextual embedding is the sum over a window of ±1 neighbours. That embedding is hashed into a d = 32-bit signature: bit k is the sign of its projection on a Gaussian random hyperplane (Appendix G of the paper). Signatures are appended to the Signature DWM.
- **Query:** content keywords of the question (a stop-word filter stands in for the paper's LLM keyword prompt) are hashed the same way. The stored signatures, decoded from the Signature DWM, are scanned with XOR + popcount, and positions within Hamming radius r = 8 are mapped to entries through the metadata.
- **Metadata validation:** candidate entries are ranked by how many query keywords co-occur in their span, then by Hamming closeness. Exact signature co-occurrence adds a bonus, checked with DWM `rank(c, beta) - rank(c, alpha) > 0`; `rank(c, n)` orders the query signatures by frequency.
- **Reconstruction:** the top 10 entries are rebuilt from the Content DWM.

Settings: D = 512 and d = 32 are taken from the paper. The radius, window and query window are not given in the paper; they were chosen on the training conversations only. Seed 13. `method/wavelet_selftest.py` checks `access`/`rank`/`select`. The implementation is from scratch; no public code exists.
