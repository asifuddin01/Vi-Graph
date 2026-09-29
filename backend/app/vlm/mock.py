"""Deterministic stand-in VLM: no GPU, no weights, ignores the image.

Used for development, tests, and the default Docker image. It returns scripted responses in
order and keeps repeating the last one once the script runs out, so tests can drive the
Stage C retry/repair path (e.g. ``MockVLM(["not json", valid_json])``).
"""

from __future__ import annotations

import json
import threading
from collections import deque
from collections.abc import Sequence

from app.vlm.base import Completion, DecodingParams, Message, ModelInfo, VLMBackend

MOCK_MODEL_ID = "vigraph/mock-vlm"
MOCK_REVISION = "1"

# The canonical schema v2 example from spec §7.
_DEFAULT_GRAPH = {
    "schema_version": "2.0",
    "diagram_type": "neural_network",
    "nodes": [
        {"id": "n1", "label": "Input Image", "type": "input", "group_id": None},
        {"id": "n2", "label": "CNN Encoder", "type": "module", "group_id": None},
        {"id": "n3", "label": "Transformer Encoder", "type": "module", "group_id": None},
        {"id": "n4", "label": "Feature Fusion", "type": "fusion", "group_id": None},
        {"id": "n5", "label": "Classifier", "type": "output", "group_id": None},
    ],
    "edges": [
        {"source": s, "target": t, "relation": "flows_to", "label": None, "condition": None}
        for s, t in [("n1", "n2"), ("n1", "n3"), ("n2", "n4"), ("n3", "n4"), ("n4", "n5")]
    ],
}
DEFAULT_RESPONSE = json.dumps(_DEFAULT_GRAPH, indent=2)

_MAX_RECORDED_CALLS = 64


class MockVLM(VLMBackend):
    def __init__(self, responses: Sequence[str] | None = None) -> None:
        self._responses = list(responses) if responses else [DEFAULT_RESPONSE]
        self._lock = threading.Lock()
        self.call_count = 0
        # Recent conversations, for test assertions; bounded so a long-running server
        # using the mock doesn't grow without limit.
        self.calls: deque[list[Message]] = deque(maxlen=_MAX_RECORDED_CALLS)

    @property
    def info(self) -> ModelInfo:
        return ModelInfo(backend="mock", model_id=MOCK_MODEL_ID, revision=MOCK_REVISION)

    def _generate(self, messages: Sequence[Message], params: DecodingParams) -> Completion:
        with self._lock:
            text = self._responses[min(self.call_count, len(self._responses) - 1)]
            self.call_count += 1
            self.calls.append(list(messages))
        return Completion(text=text, finish_reason="stop")
