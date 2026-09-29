"""Smoke-test the configured VLM on one image (from backend/).

    python -m app.vlm path/to/diagram.png
    VIGRAPH_VLM_BACKEND=hf VIGRAPH_VLM_DTYPE=float16 python -m app.vlm diagram.png

Prints the raw model output and its reproducibility metadata. It does not validate or
repair the output; that is the pipeline's job.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.config import get_settings
from app.utils.images import ImageError, preprocess_image
from app.vlm.base import DecodingParams
from app.vlm.factory import get_vlm_backend
from app.vlm.prompts import GRAPH_EXTRACTION, build_extraction_messages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.vlm", description=__doc__.split("\n")[0])
    parser.add_argument("image", type=Path)
    parser.add_argument("--max-new-tokens", type=int, default=DecodingParams().max_new_tokens)
    args = parser.parse_args(argv)

    settings = get_settings()
    try:
        prepared = preprocess_image(
            args.image.read_bytes(),
            max_side=settings.image_max_side,
            max_pixels=settings.image_max_pixels,
        )
    except (OSError, ImageError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    output = get_vlm_backend().generate(
        build_extraction_messages([prepared.image]),
        DecodingParams(max_new_tokens=args.max_new_tokens),
    )
    print(output.text)
    metadata = output.model_dump(mode="json", exclude={"text"})
    metadata["prompt"] = {"id": GRAPH_EXTRACTION.id, "sha256": GRAPH_EXTRACTION.sha256}
    metadata["image"] = {"sha256": prepared.sha256, "size": list(prepared.image.size)}
    print(json.dumps(metadata, indent=2), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
