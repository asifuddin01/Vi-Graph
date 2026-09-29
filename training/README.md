# Training (Colab T4 only)

All fine-tuning runs in **Google Colab on a T4 GPU** (spec §18). The backend never trains —
it only loads a saved LoRA adapter via `VIGRAPH_VLM_ADAPTER_PATH`.

| Path         | Contents                                              |
| ------------ | ----------------------------------------------------- |
| `configs/`   | Training configs (model, LoRA, quantization, schedule) |
| `scripts/`   | Training / checkpoint-resume scripts                   |
| `notebooks/` | Colab notebooks                                        |

## Rules

- 4-bit quantization + LoRA/QLoRA; no full fine-tuning, no training from scratch.
- Checkpoint to Google Drive frequently and support resume after disconnects.
- Log reproducibility metadata for every run (§18.1): model + revision, LoRA config,
  quantization, prompt hash, decoding params, seed, `schema_version`, split hash.
- Never train on the test split.

Adapters and checkpoints are not committed to git.
