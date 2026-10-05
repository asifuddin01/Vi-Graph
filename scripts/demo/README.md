# Demo video and screenshots

These scripts produced [`docs/demo/`](../../docs/demo/): the video (`vigraph-demo.mp4`,
`vigraph-demo.gif`) and the screenshots. They come from one scripted run of the real app,
with the frontend and backend running unchanged.

**Where the model output comes from.** `replay_server.py` starts the backend with a replay
VLM. It does not run the model. For each uploaded test image, it returns the raw text the
fine-tuned model generated for that exact image in the final evaluation run
(`evaluation/reports/qwen3vl-2b-qlora-a6000-v1-final-greedy`, RTX 4080 SUPER). It then waits
as long as that generation took. Everything after the model runs live: Stage C validation,
Stage D normalization, the graph layer, Mermaid, the editor and graph-based QA. The app
labels the backend `VLM: replay`. This works without a GPU, and the results match the
published evaluation.

How the replay works:

- **Matching images:** images are matched to recordings by content (SHA-256 of the file),
  not by file name.
- **Questions:** questions that need the model itself (visual or "why" questions) get a
  503 ("the model backend failed"), because there is no recorded answer to replay. Graph
  questions work.

To show the live model instead, run the backend with `VIGRAPH_VLM_BACKEND=hf` and the
adapter (see [`models/`](../../models/qwen3vl-2b-qlora-a6000-v1/README.md)). After that,
`record_demo.mjs` works the same.

## Re-recording

You need:

- the 500 synthetic-v1 test images that run used (the Windows Graphviz 16.1 build, split hash
  `88ae7d75…`);
- Playwright with Chromium for Node;
- an `ffmpeg` with libx264.

```bash
# 1. backend (replay) and frontend
PYTHONPATH=backend:. .venv/bin/python scripts/demo/replay_server.py \
    evaluation/reports/qwen3vl-2b-qlora-a6000-v1-final-greedy path/to/test-images
(cd frontend && npm run build && npx next start -p 3000)

# 2. walkthrough → frames + screenshots, then encode (about 2 minutes)
NODE_PATH="$(npm root -g)" node scripts/demo/record_demo.mjs path/to/test-images /tmp/demo
scripts/demo/encode.sh /tmp/demo
```

Restart `replay_server.py` before each recording. Its storage is new on every start, so
results don't show up as "cached" or with old answers.

**How the video is made.** It uses Chromium's screencast at 1920×1200, not Playwright's
recorder (whose text is blurry), plus a drawn cursor and captions. Screenshots are taken at
2× pixel density with the overlays hidden. The model wait is shortened to 2.5 s in the
video, and the caption after it gives the real time.

**The diagrams.** `test-000381` (scientific workflow), `test-000181` (ML pipeline) and
`test-000329` (system architecture) were picked because the model got them right on the
first attempt (graph similarity 1.0, correct edge labels). They show the app working; they
are not a sample of typical results.
