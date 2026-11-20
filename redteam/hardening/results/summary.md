| run | valid | recall@10 | hit@1 | answer-token recall | worst category | context tokens | rank delta | paired recall diff (95% CI) |
|---|---|---:|---:|---:|---:|---:|---:|---|
| better_bm25_context | True | 74.72 | 54.17 | 66.03 | 57.24 | 357.9 | +4.912 | +48.38 [+44.58, +52.19] |
| bm25_baseline | True | 69.05 | 48.25 | 62.40 | 46.41 | 349.1 | +4.220 | +42.73 [+39.05, +46.57] |
| sc_public_label_avoid_bm25 | True | 55.73 | 39.76 | 55.71 | 34.77 | 315.8 | +3.066 | +29.49 [+25.34, +33.77] |
| sc_public_label_prior_bm25 | True | 51.39 | 15.63 | 57.19 | 35.63 | 406.1 | +2.148 | +25.03 [+21.01, +29.30] |
| better_bm25_rerank | True | 38.34 | 35.51 | 51.06 | 23.92 | 429.9 | +1.712 | +11.98 [+9.72, +14.42] |
| hippocampus_seed15 | True | 27.81 | 8.35 | 46.15 | 12.64 | 511.9 | +0.083 | +1.45 [-2.07, +5.00] |
| hippocampus_seed14 | True | 26.23 | 9.71 | 46.06 | 10.92 | 505.2 | +0.018 | -0.11 [-3.74, +3.71] |
| hippocampus | True | 26.39 | 9.10 | 46.25 | 10.49 | 507.8 | +0.000 |  |
| sc_forged_fields | True | 26.39 | 9.10 | 46.25 | 10.49 | 507.8 | +0.000 | +0.00 [+0.00, +0.00] |
| sc_prewrite_scores | True | 26.39 | 9.10 | 46.25 | 10.49 | 507.8 | +0.000 | +0.00 [+0.00, +0.00] |
| sc_relabel_hidden_absolute | True | 26.39 | 9.10 | 46.25 | 10.49 | 507.8 | +0.000 | +0.00 [+0.00, +0.00] |
| sc_relabel_visible_data | True | 26.39 | 9.10 | 46.25 | 10.49 | 507.8 | +0.000 | +0.00 [+0.00, +0.00] |
| sc_public_label_avoid_reference | True | 24.44 | 8.35 | 42.52 | 12.93 | 444.3 | -0.046 | -1.85 [-4.16, +0.56] |
| better_idf_weighting | True | 22.38 | 6.68 | 43.71 | 13.10 | 516.7 | -0.250 | -3.92 [-6.27, -1.71] |
| legacy_iter10_config | True | 13.38 | 3.95 | 38.89 | 5.17 | 484.6 | -0.943 | -12.96 [-16.45, -9.20] |
| weaker_16bit | True | 10.96 | 2.58 | 38.51 | 5.75 | 578.1 | -1.199 | -15.39 [-18.42, -12.20] |
| sc_longest_entries | True | 5.17 | 0.30 | 41.58 | 2.59 | 775.1 | -1.779 | -21.18 [-24.39, -18.00] |
| recency_baseline | False | 0.00 | 0.00 | 0.00 | 0.00 | 785.0 | -2.771 |  |
| weaker_one_bit | False | 0.00 | 0.00 | 0.00 | 0.00 | 785.0 | -2.771 |  |
| sc_empty_output | False | 0.00 | 0.00 | 0.00 | 0.00 | 785.0 | -2.771 |  |
| sc_hidden_labels_absolute | False | 0.00 | 0.00 | 0.00 | 0.00 | 785.0 | -2.771 |  |
| sc_hidden_labels_relative | False | 0.00 | 0.00 | 0.00 | 0.00 | 785.0 | -2.771 |  |
| sc_over_budget | False | 0.00 | 0.00 | 0.00 | 0.00 | 785.0 | -2.771 |  |
| sc_public_locomo_labels | False | 0.00 | 0.00 | 0.00 | 0.00 | 785.0 | -2.771 |  |
| sc_single_wrong_id | False | 0.00 | 0.00 | 0.00 | 0.00 | 785.0 | -2.771 |  |
| sc_train_label_lookup | False | 0.00 | 0.00 | 0.00 | 0.00 | 785.0 | -2.771 |  |
| sc_hidden_labels_absolute_realws | False | 0.00 | 0.00 | 0.00 | 0.00 | 785.0 | -2.771 |  |
| sc_hidden_labels_relative_realws | False | 0.00 | 0.00 | 0.00 | 0.00 | 785.0 | -2.771 |  |
| sc_namespace_escape_realws | False | 0.00 | 0.00 | 0.00 | 0.00 | 785.0 | -2.771 |  |
