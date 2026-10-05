"""Serve the app with a replay VLM: an evaluation run's recorded model outputs, for screenshots.

    PYTHONPATH=backend:. python scripts/demo/replay_server.py RUN_DIR IMAGES_DIR [--port 8000]

The model is not run here. For an uploaded image, the replay backend returns what the model
produced for the same image in RUN_DIR (every attempt, in order), and by default it waits as
long as that generation took on the GPU, so the UI's latency is the recorded one (--no-wait
skips the wait). Everything after the model runs live: Stage C validation, Stage D
normalization, the graph layer, Mermaid, the editor and graph-based QA. /health reports the
backend as "replay", so screenshots say what they show. Questions that need the model itself
(visual / "why") get a 503, as for any model failure: there is no recorded answer to replay.

Images are matched by content: every file in IMAGES_DIR whose sha256 equals a recorded
sample's image hash is preprocessed as the app does, and those pixels identify the sample
when it is uploaded. Storage goes to a temporary directory unless VIGRAPH_STORAGE_DIR is set.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tempfile
import time
from collections.abc import Sequence
from pathlib import Path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="replay_server.py")
    parser.add_argument("run_dir", type=Path, help="evaluation run with predictions.jsonl(.gz)")
    parser.add_argument("images", type=Path, help="folder with the run's input images")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-wait", action="store_true", help="don't replay generation time")
    args = parser.parse_args(argv)

    from evaluation.results import read_results, read_run

    run = read_run(args.run_dir)
    # The app must see images exactly as the run did; set before the app reads its settings.
    os.environ["VIGRAPH_IMAGE_MAX_SIDE"] = str(run.config.image_max_side)
    os.environ.setdefault("VIGRAPH_STORAGE_DIR", tempfile.mkdtemp(prefix="vigraph-replay-"))
    os.environ["VIGRAPH_ANALYZE_RATE_LIMIT_PER_MINUTE"] = "0"
    os.environ["VIGRAPH_QA_RATE_LIMIT_PER_MINUTE"] = "0"

    import uvicorn

    from app.config import get_settings
    from app.main import create_app
    from app.utils.images import preprocess_image
    from app.vlm.base import Completion, DecodingParams, Message, ModelInfo, VLMBackend
    from app.vlm.factory import get_vlm_backend
    from app.vlm.prompts import GRAPH_EXTRACTION

    settings = get_settings()
    extraction_prompt = GRAPH_EXTRACTION.text

    def pixels_key(image) -> str:
        header = f"{image.mode}:{image.size}".encode()
        return hashlib.sha256(header + image.tobytes()).hexdigest()

    recorded = {}
    for result in read_results(args.run_dir):
        analysis = result.prediction.analysis
        if analysis is not None:
            recorded[analysis.image.sha256] = (result.sample_id, analysis)
    replays = {}
    for path in sorted(args.images.iterdir()):
        data = path.read_bytes()
        match = recorded.get(hashlib.sha256(data).hexdigest())
        if match is None:
            continue
        prepared = preprocess_image(
            data, max_side=settings.image_max_side, max_pixels=settings.image_max_pixels
        )
        replays[pixels_key(prepared.image)] = match
    if not replays:
        print(f"no image in {args.images} matches a recorded sample of {run.name}", file=sys.stderr)
        return 1
    model = next(iter(replays.values()))[1].extraction.attempts[0].output.model

    class ReplayVLM(VLMBackend):
        @property
        def info(self) -> ModelInfo:
            return ModelInfo(
                backend="replay",
                model_id=model.model_id,
                revision=model.revision,
                adapter_path=f"{run.name} (recorded outputs)",
            )

        def _generate(self, messages: Sequence[Message], params: DecodingParams) -> Completion:
            if messages[0].text != extraction_prompt or not messages[0].images:
                raise RuntimeError("the replay backend only has recorded graph extractions")
            match = replays.get(pixels_key(messages[0].images[0]))
            if match is None:
                raise RuntimeError(f"this image is not one of the {len(replays)} recorded samples")
            sample_id, analysis = match
            turn = len(messages) // 2  # 0 = first attempt, 1 = the Stage C retry
            attempts = analysis.extraction.attempts
            if turn >= len(attempts):
                raise RuntimeError(f"{sample_id}: the run recorded only {len(attempts)} attempt(s)")
            output = attempts[turn].output
            if not args.no_wait:
                time.sleep(output.latency_ms / 1000)
            print(f"replay {sample_id} attempt {turn + 1}", file=sys.stderr)
            return Completion(**output.model_dump(include=set(Completion.model_fields)))

    app = create_app(settings)
    replay = ReplayVLM()
    app.dependency_overrides[get_vlm_backend] = lambda: replay
    app.dependency_overrides[get_settings] = lambda: settings.model_copy(
        update={"vlm_backend": "replay"}
    )
    print(f"{run.name}: {len(replays)} images can be replayed", file=sys.stderr)
    uvicorn.run(app, host="127.0.0.1", port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
