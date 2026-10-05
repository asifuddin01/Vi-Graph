# Vi-Graph QLoRA adapter v1 (Qwen3-VL-2B-Instruct)

This is a LoRA adapter for
[Qwen/Qwen3-VL-2B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct) (revision
`89644892e4d85e24eaac8bacfd4f463576704203`). It reads a diagram image and writes the Vi-Graph
schema 2.0 graph JSON using the `graph_extraction@1` prompt. Every QLoRA result in this
repository comes from this adapter.

| File                        | Bytes      | SHA-256                                                            |
| --------------------------- | ---------- | ------------------------------------------------------------------ |
| `adapter_model.safetensors` | 69,788,264 | `7a0d034fe3c680536540352a9419be6f91b759cfccbe101fda421b2e59247165` |
| `adapter_config.json`       | 1,231      | `9ab63c9f4d5191134011b7de48800c45a9b785b5fdef35dd455d207c28a684a0` |

The checksums match the training hand-back
([`training/runs/qwen3vl-2b-qlora-a6000-v1/handback_MANIFEST.json`](../../training/runs/qwen3vl-2b-qlora-a6000-v1/handback_MANIFEST.json)).
`training/tests/test_committed_adapter.py` checks them.

## Training

- **Method:** QLoRA. The base model was 4-bit NF4; LoRA r 16, alpha 32, dropout 0.05 on the
  language model's q/k/v/o and gate/up/down projections.
- **Data:** the synthetic-v1 train split (2,000 diagrams). It never saw the test split; the
  test split uses held-out layouts and themes.
- **Run:** 250 steps in bf16 with images at 896 px longest side, 1.36 h on an RTX A6000. Peak
  memory was 7.6 GB allocated.
- **Metadata:** config, loss log and §18.1 metadata are in
  [`training/runs/qwen3vl-2b-qlora-a6000-v1/`](../../training/runs/qwen3vl-2b-qlora-a6000-v1/).

## Results

Scores on all 500 synthetic-v1 test diagrams (greedy, 896 px, 2048 tokens, runaway guard on;
macro means, failures count as 0):

| System                | Graph similarity | Edge F1 | Structural QA | Valid graphs |
| --------------------- | ---------------- | ------- | ------------- | ------------ |
| This adapter          | 0.740            | 0.638   | 0.582         | 91.0%        |
| Zero-shot base model  | 0.581            | 0.499   | 0.437         | 72.0%        |
| OCR + OpenCV baseline | 0.738            | 0.610   | 0.450         | 99.8%        |

These are synthetic diagrams only; the adapter has not been tested on real ones. The
[report](../../research/paper/report.md) has the full results and limitations.

## Use

You need a GPU and `pip install -r requirements-vlm.txt`. The base model downloads from
huggingface.co on first use.

Run the app from `backend/`:

```bash
VIGRAPH_VLM_BACKEND=hf \
VIGRAPH_VLM_ADAPTER_PATH=../models/qwen3vl-2b-qlora-a6000-v1 \
VIGRAPH_VLM_REVISION=89644892e4d85e24eaac8bacfd4f463576704203 \
VIGRAPH_VLM_DTYPE=bfloat16 \
VIGRAPH_IMAGE_MAX_SIDE=896 \
../.venv/bin/uvicorn app.main:app
```

Evaluate it from the repo root:

```bash
PYTHONPATH=backend python -m evaluation run --dataset data/synthetic/synthetic-v1 \
    --split test --backend hf --dtype bfloat16 --image-max-side 896 \
    --max-new-tokens 2048 --runaway-guard \
    --adapter models/qwen3vl-2b-qlora-a6000-v1 --out /tmp/qlora-test
```

Usage notes:

- **Image size:** the adapter was trained at 896 px. In the resolution ablation, 768 to
  1024 px scored the same and 640 px scored worse, so keep `VIGRAPH_IMAGE_MAX_SIDE` in
  768–1024.
- **dtype:** use float16 instead of bfloat16 on GPUs without bfloat16 (e.g. a T4). That
  combination has not been evaluated.
- **Reproducibility:** greedy outputs can differ between GPU models. On the same 112
  diagrams, an A6000 and a 4080 SUPER agreed on every metric within ±0.009.

## License

The adapter ships with this repository under its MIT license. The base model it modifies is
licensed separately by Qwen under Apache-2.0, and that license applies to the base weights.
