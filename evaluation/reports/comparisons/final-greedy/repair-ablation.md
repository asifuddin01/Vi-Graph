# Repair ablation (§24D): first attempt as-is vs final output

## qwen3vl-2b-qlora-a6000-v1-final-greedy (500 samples)

| Metric | First attempt (raw) | Final (Stage C + D) | Δ | 95% CI | p (Holm) |
| --- | --- | --- | --- | --- | --- |
| valid | 0.728 | 0.910 | +0.182 | [+0.150, +0.216] | 0.0006 |
| node_f1 | 0.696 | 0.854 | +0.158 | [+0.129, +0.189] | 0.0006 |
| edge_f1 | 0.534 | 0.638 | +0.104 | [+0.083, +0.126] | 0.0006 |
| edge_strict_f1 | 0.509 | 0.611 | +0.102 | [+0.082, +0.124] | 0.0006 |
| graph_similarity | 0.610 | 0.740 | +0.130 | [+0.106, +0.156] | 0.0006 |
| diagram_type_accuracy | 0.708 | 0.882 | +0.174 | [+0.142, +0.208] | 0.0006 |

| Final graph from | Samples | Mean graph similarity |
| --- | --- | --- |
| valid_first_attempt | 364 | 0.838 |
| valid_after_retry | 26 | 0.721 |
| repaired | 65 | 0.713 |
| failed | 45 | 0.000 |

Attempts per sample: {1: 364, 2: 136}

## qwen3-vl-2b-instruct-zeroshot-final-greedy (500 samples)

| Metric | First attempt (raw) | Final (Stage C + D) | Δ | 95% CI | p (Holm) |
| --- | --- | --- | --- | --- | --- |
| valid | 0.512 | 0.720 | +0.208 | [+0.174, +0.244] | 0.0006 |
| node_f1 | 0.500 | 0.703 | +0.203 | [+0.168, +0.238] | 0.0006 |
| edge_f1 | 0.357 | 0.499 | +0.142 | [+0.116, +0.170] | 0.0006 |
| edge_strict_f1 | 0.293 | 0.415 | +0.123 | [+0.099, +0.148] | 0.0006 |
| graph_similarity | 0.414 | 0.581 | +0.167 | [+0.138, +0.196] | 0.0006 |
| diagram_type_accuracy | 0.276 | 0.334 | +0.058 | [+0.038, +0.080] | 0.0006 |

| Final graph from | Samples | Mean graph similarity |
| --- | --- | --- |
| valid_first_attempt | 256 | 0.811 |
| valid_after_retry | 34 | 0.895 |
| repaired | 70 | 0.753 |
| failed | 140 | 0.000 |

Attempts per sample: {1: 256, 2: 244}
