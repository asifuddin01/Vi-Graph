# Mermaid escaping check

`backend/app/exporters/mermaid.py` escapes labels for Mermaid (spec §10, §29). Mermaid's
grammar changes between releases, so **re-run this whenever the `mermaid` package is
upgraded**. It renders adversarial labels (quotes, `#`, `;`, pipes, HTML tags, markdown
backticks, entity look-alikes, keywords, backslashes) with the frontend's own Mermaid
bundle in headless Chromium and fails unless every label parses, renders, and displays
literally.

```bash
# from the repo root; needs frontend/node_modules and Playwright with Chromium
PYTHONPATH=backend .venv/bin/python scripts/verify_mermaid/cases.py > /tmp/mermaid_cases.json
NODE_PATH="$(npm root -g)" node scripts/verify_mermaid/check.mjs /tmp/mermaid_cases.json
```

Last verified: mermaid 12.0.0 — all cases pass.
