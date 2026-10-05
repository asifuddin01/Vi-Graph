"""The trained adapter committed in models/ is the one the training run handed back."""

import hashlib
import json
import re
import struct
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADAPTER = REPO / "models" / "qwen3vl-2b-qlora-a6000-v1"
RUN = REPO / "training" / "runs" / "qwen3vl-2b-qlora-a6000-v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def test_files_match_the_handback_manifest() -> None:
    manifest = json.loads((RUN / "handback_MANIFEST.json").read_text())
    prefix = "training/qwen3vl-2b-qlora-a6000-v1/adapter/"
    expected = {
        f["path"].removeprefix(prefix): (f["bytes"], f["sha256"])
        for f in manifest["files"]
        if f["path"].startswith(prefix)
    }

    assert set(expected) == {"adapter_model.safetensors", "adapter_config.json"}
    for name, (size, digest) in expected.items():
        path = ADAPTER / name
        assert (path.stat().st_size, sha256(path)) == (size, digest), name
    assert (ADAPTER / "adapter_config.json").read_bytes() == (
        RUN / "adapter_config.json"
    ).read_bytes()


def test_weights_agree_with_the_lora_config() -> None:
    config = json.loads((ADAPTER / "adapter_config.json").read_text())
    with (ADAPTER / "adapter_model.safetensors").open("rb") as f:
        (length,) = struct.unpack("<Q", f.read(8))
        header = json.loads(f.read(length))
    header.pop("__metadata__", None)
    modules = Counter(re.search(r"\.(\w+)\.lora_[AB]\.weight$", name)[1] for name in header)
    ranks = {tensor["shape"][0 if ".lora_A." in name else 1] for name, tensor in header.items()}

    assert config["base_model_name_or_path"] == "Qwen/Qwen3-VL-2B-Instruct"
    assert set(modules) == set(config["target_modules"])
    assert set(modules.values()) == {2 * 28}  # A and B in each of the 28 decoder layers
    assert ranks == {config["r"]} == {16}
    assert all(".language_model." in name for name in header)
