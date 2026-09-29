"""OCR step of the classical baseline (Tesseract through pytesseract).

Text is read per shape: each shape's interior is cropped, everything outside it (the
outline, neighbouring strokes) blanked, polarity normalized to dark-on-light, and the crop
scaled so letters are ~25 px tall. Tesseract's page segmentation is unreliable on whole
diagrams (box outlines close to words confuse it); on clean crops it reads well.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
import pytesseract

MIN_CONFIDENCE = 40.0
TARGET_LETTER_HEIGHT = 25.0
PAD = 12


@dataclass
class TextLine:
    text: str
    x0: int
    y0: int
    x1: int
    y1: int
    confidence: float

    @property
    def center(self) -> tuple[float, float]:
        return (self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2

    @property
    def height(self) -> int:
        return self.y1 - self.y0


def read_region(
    gray: np.ndarray, ink: np.ndarray, keep: np.ndarray, *, sparse: bool = False
) -> list[TextLine]:
    """Text in the pixels ``keep`` of ``gray``; ``ink`` marks strokes/text (thin structures).

    Returns lines in image coordinates. ``sparse`` for scattered text (whole-image pass,
    group interiors); otherwise the crop is read as one block.
    """
    text_pixels = ink & keep
    ys, xs = np.nonzero(text_pixels)
    if len(xs) < 8:
        return []
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    crop = gray[y0:y1, x0:x1].astype(np.float32)
    text = text_pixels[y0:y1, x0:x1]
    paper = keep[y0:y1, x0:x1] & ~text
    paper_level = float(np.median(crop[paper])) if paper.any() else 255.0 - float(crop[text].mean())
    if float(crop[text].mean()) > paper_level:  # light text on a dark fill: invert
        crop, paper_level = 255.0 - crop, 255.0 - paper_level
    crop[~keep[y0:y1, x0:x1]] = paper_level
    # Stretch so paper is white and text is dark.
    ink_level = float(np.percentile(crop[text], 10))
    span = max(paper_level - ink_level, 1.0)
    crop = np.clip((crop - ink_level) / span * 255.0, 0, 255).astype(np.uint8)

    factor = float(np.clip(TARGET_LETTER_HEIGHT / _letter_height(text), 1.0, 4.0))
    big = cv2.resize(crop, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
    big = cv2.copyMakeBorder(big, PAD, PAD, PAD, PAD, cv2.BORDER_CONSTANT, value=255)
    psm = 11 if sparse else 6
    data = pytesseract.image_to_data(
        big, config=f"--psm {psm} --oem 1", output_type=pytesseract.Output.DICT
    )
    words = []
    for i, word in enumerate(data["text"]):
        word = word.strip()
        confidence = float(data["conf"][i])
        if not word or confidence < MIN_CONFIDENCE or not any(c.isalnum() for c in word):
            continue
        left, top = (data["left"][i] - PAD) / factor + x0, (data["top"][i] - PAD) / factor + y0
        width, height = data["width"][i] / factor, data["height"][i] / factor
        words.append(
            TextLine(
                word,
                int(left),
                int(top),
                int(left + width + 0.999),
                int(top + height + 0.999),
                confidence,
            )
        )
    return join_lines(words)


def _letter_height(text: np.ndarray) -> float:
    count, _, stats, _ = cv2.connectedComponentsWithStats(text.astype(np.uint8), connectivity=8)
    heights = stats[1:, cv2.CC_STAT_HEIGHT]
    heights = heights[heights >= 3]
    return float(np.median(heights)) if len(heights) else 10.0


def join_lines(words: list[TextLine]) -> list[TextLine]:
    """Merge words that sit on one baseline and are about a space apart into lines."""
    lines: list[TextLine] = []
    for word in sorted(words, key=lambda w: (w.x0, w.y0)):
        for line in lines:
            height = max(line.height, word.height, 1)
            same_row = abs(line.center[1] - word.center[1]) < 0.5 * height
            gap = word.x0 - line.x1
            if same_row and -0.3 * height <= gap <= 1.2 * height:
                n = len(line.text.split())
                line.text = f"{line.text} {word.text}"
                line.x1 = max(line.x1, word.x1)
                line.y0, line.y1 = min(line.y0, word.y0), max(line.y1, word.y1)
                line.confidence = (line.confidence * n + word.confidence) / (n + 1)
                break
        else:
            lines.append(TextLine(word.text, word.x0, word.y0, word.x1, word.y1, word.confidence))
    return lines
