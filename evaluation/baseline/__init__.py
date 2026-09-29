"""Classical non-VLM baseline (spec §19.1): OCR + geometry → graph.

Needs the optional dependencies in requirements-baseline.txt and the Tesseract binary
(``apt-get install tesseract-ocr``).
"""

from __future__ import annotations

import time
from importlib.metadata import version

import cv2
import pytesseract

from evaluation.baseline.pipeline import (
    BASELINE_VERSION,
    HEAD_RATIO,
    INK_CONTRAST,
    INK_WINDOW,
    BaselineResult,
    reconstruct,
)
from evaluation.predictors import Prediction, Predictor
from evaluation.samples import EvalSample

__all__ = ["BASELINE_VERSION", "BaselinePredictor", "BaselineResult", "reconstruct"]


class BaselinePredictor(Predictor):
    name = f"baseline:v{BASELINE_VERSION}"

    def predict(self, sample: EvalSample) -> Prediction:
        start = time.perf_counter()
        result = reconstruct(sample.image.read_bytes())
        return Prediction(
            graph=result.graph,
            first_attempt_graph=result.graph,  # no retry or repair: raw output = final output
            validity=None,
            analysis=None,
            latency_ms=(time.perf_counter() - start) * 1000,
            notes=result.notes,
        )

    def describe(self) -> dict[str, object]:
        return {
            "baseline_version": BASELINE_VERSION,
            "tesseract": str(pytesseract.get_tesseract_version()),
            "opencv": cv2.__version__,
            "pytesseract": version("pytesseract"),
            "ink_window": INK_WINDOW,
            "ink_contrast": INK_CONTRAST,
            "head_ratio": HEAD_RATIO,
        }
