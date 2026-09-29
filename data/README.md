# Data

| Path           | Contents                                                                  |
| -------------- | ------------------------------------------------------------------------- |
| `generator/`   | Synthetic dataset generator: graphs, renderer, dataset builder (§13–16)   |
| `raw/`         | Unprocessed source images                                                 |
| `synthetic/`   | Generated datasets (gitignored, rebuild with the CLI below)               |
| `real/`        | Manually verified real-world diagrams, spec §15                           |
| `annotations/` | Ground-truth annotations, incl. inter-annotator agreement records (§15.1) |
| `splits/`      | Committed manifests + stats of each dataset build, pinned by hashes       |

## Rules

- **Never train on the test set.** Keep one untouched benchmark set for final reporting.
- The test split must contain layouts/templates not seen in training (§16).
- Every real image records its source and license. Do not commit copyrighted images to a
  public dataset without permission (§15).
- Generated images are not committed (they are regenerable); split manifests and
  annotations are.

## Synthetic dataset

Needs Graphviz (`apt-get install graphviz fonts-dejavu-core`). From the repo root:

```bash
PYTHONPATH=backend python -m data.generator build --out data/synthetic/synthetic-v1
PYTHONPATH=backend python -m data.generator verify data/synthetic/synthetic-v1 \
    --reference data/splits/synthetic-v1.manifest.json
PYTHONPATH=backend python -m data.generator stats data/synthetic/synthetic-v1
```

`build` writes `images/<id>.png`, `graphs/<id>.json` (schema v2 ground truth),
`metadata.jsonl` (graph spec, render parameters, hashes per sample), `splits/<split>.txt`
and `manifest.json`. The default `synthetic-v1` is 2000 train / 300 val / 500 test (§32),
seed 0; it takes about 40 s on 8 threads and 190 MB.

### Splits

| Split  | Layouts                          | Themes                                       | Use                  |
| ------ | -------------------------------- | -------------------------------------------- | -------------------- |
| train  | layered_lr, force                | classic, pastel, corporate, vivid, sketch    | training             |
| val    | layered_lr, force                | classic, pastel, corporate, vivid, sketch    | model selection      |
| test   | layered_tb, radial, circular     | dark, blueprint, paper                       | held out, final only |

Every split is stratified over difficulty levels L1–L4 and the seven diagram types. The
test split's layouts and themes never appear in training, so its scores measure diagram
reading rather than template memorization (§16). `--iid-test N` adds an in-distribution
`test_iid` split for measuring the size of that shift.

### Hashes

`manifest.json` pins each split twice:

- `split_hashes` — ids + image hashes + ground-truth hashes. This is the split version
  logged with every evaluation run (§18.1).
- `graph_hashes` — ids + ground-truth hashes only. Rendered pixels depend on the Graphviz
  version (Colab's apt Graphviz differs from the one used here), but the ground truth
  must not: `verify --reference data/splits/synthetic-v1.manifest.json` fails if a rebuild
  anywhere produced different graphs.

Committed `synthetic-v1` build (Graphviz 2.43.0): dataset hash
`6edd5f6328c9fd9fce15d556e99cd544a0efa571bc5a2035936592f16dee32e6`.

### Determinism

Graph generation is pure Python seeded per sample (`"{seed}:{split}:{index}"`), so any
sample can be regenerated alone and builds are identical regardless of thread count.
Rendering is deterministic for a fixed Graphviz version: the force layout uses `neato`
with a fixed `start` seed and `overlap=scale` (`fdp`, and `neato` with `overlap=false`,
were not reproducible across runs), and groups are only drawn by `dot` (clusters).

Eight example images with their ground truth are in `examples/diagrams/` and
`examples/outputs/`.
