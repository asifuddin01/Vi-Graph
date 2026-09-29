"""Classical baseline: OCR + geometry → graph, no VLM (spec §19.1). BASELINE_VERSION pins it.

    image → ink: thin structures (strokes, outlines, text), independent of fill colours
          → shapes: enclosed background regions with ink inside are nodes; a region that
            encloses other shapes is a group
          → OCR (Tesseract) per shape on a cleaned crop: node labels; group labels from the
            band along a group's top edge; one sparse pass over the rest for edge labels
          → arrows: strokes left after removing nodes and text; where a stroke meets a node,
            a lot of ink (an arrowhead) marks a target and a bare line end marks a source
          → rule-based assembly: labels from the text inside each node, edge labels from
            free text next to a stroke, types from shape and position

Deliberately generic: no knowledge of the synthetic generator's themes, fonts, shapes or
vocabularies beyond a short list of domain keywords for guessing diagram_type. Everything
is scale-relative (to the median text height). It is expected to degrade quickly with
complexity; that is the point of the comparison (§19.1, H6).
"""

from __future__ import annotations

import io
from collections import Counter
from dataclasses import dataclass, field

import cv2
import numpy as np
from PIL import Image
from pydantic import ValidationError

from app.schemas import DiagramGraph
from evaluation.baseline.ocr import TextLine, read_region

BASELINE_VERSION = "1"

INK_CONTRAST = 50  # grey levels from the local median: strokes, outlines and text
INK_WINDOW = 21  # px; wider than strokes and arrowheads, narrower than shape fills
HEAD_RATIO = 1.5  # an end with ≥ this × the ink of the thinnest end is an arrowhead
FREE_TEXT_CONFIDENCE = 60.0
FILL_CONTRAST = 4  # any channel: a painted (filled) area vs the background
STROKE_ERODE = 3  # px; erosion that removes strokes but keeps filled areas
GROUP_MARGIN = 6  # px between a group's border and the shapes inside it

# Domain words → diagram type (majority vote over label words; generic vocabulary).
TYPE_KEYWORDS = {
    "neural_network": "conv layer relu gelu attention pool pooling norm softmax embedding "
    "dropout linear dense lstm gru transformer encoder decoder residual",
    "ml_pipeline": "train training model dataset features feature evaluate evaluation "
    "validation inference predict prediction hyperparameter tuning metrics",
    "data_pipeline": "extract load transform ingest etl kafka spark table warehouse "
    "stream batch parquet sql join partition dedupe clean",
    "system_architecture": "service api gateway database db cache queue server client "
    "auth load balancer frontend backend storage microservice",
    "scientific_workflow": "experiment sample samples measure measurement analysis simulation "
    "hypothesis protocol assay sequencing calibration",
    "flowchart": "start end yes no check retry done begin stop",
}


@dataclass
class Region:
    index: int
    fill: np.ndarray  # bool mask: the region with its enclosed text filled in
    bbox: tuple[int, int, int, int]  # x0, y0, x1, y1
    lines: list[TextLine]
    vertices: int  # polygon approximation of the outline
    is_group: bool = False
    filled_group: bool = False  # found as a filled area (not as an enclosed region)
    parent: int | None = None
    node_id: str = ""

    @property
    def center(self) -> tuple[float, float]:
        return (self.bbox[0] + self.bbox[2]) / 2, (self.bbox[1] + self.bbox[3]) / 2

    @property
    def label(self) -> str:
        ordered = sorted(self.lines, key=lambda t: (round(t.center[1] / max(t.height, 1)), t.x0))
        return " ".join(t.text for t in ordered)


@dataclass
class BaselineResult:
    graph: DiagramGraph | None
    notes: list[str] = field(default_factory=list)


def reconstruct(image_bytes: bytes) -> BaselineResult:
    rgb = np.asarray(Image.open(io.BytesIO(image_bytes)).convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    # Ink = thin structures (strokes, outlines, text): pixels far from their local median.
    # Large uniform fills, whatever their colour, are not ink, so every theme binarizes alike.
    ink = np.abs(gray.astype(np.int16) - cv2.medianBlur(gray, INK_WINDOW)) > INK_CONTRAST

    regions = _find_regions(ink)
    if not regions:
        return BaselineResult(None, ["no closed shapes with text inside"])
    regions = _add_filled_groups(rgb, regions)
    _assign_groups(regions)
    for region in regions:
        if not region.is_group:
            region.lines = read_region(gray, ink, region.fill)
    heights = [t.height for r in regions if not r.is_group for t in r.lines]
    if not heights:
        return BaselineResult(None, ["no readable node labels"])
    scale = float(np.median(heights))
    for region in regions:
        if region.is_group:
            region.lines = _read_group_label(gray, ink, region, regions, scale)
    regions = [r for r in regions if r.lines]
    _assign_groups(regions)  # again: unreadable shapes are gone

    occupied = np.zeros(ink.shape, bool)
    for region in regions:
        occupied |= region.fill
    free_text = [
        t
        for t in read_region(gray, ink, ~_dilate(occupied, 2), sparse=True)
        if t.confidence >= FREE_TEXT_CONFIDENCE
    ]
    nodes = [r for r in regions if not r.is_group]
    for i, region in enumerate(sorted(regions, key=lambda r: (r.center[1], r.center[0])), 1):
        region.node_id = f"n{i}"

    strokes = _stroke_mask(ink, regions, free_text, scale)
    edges = _find_edges(strokes, nodes, scale)
    labels = _label_edges(edges, free_text, strokes, scale)
    graph = _assemble(regions, edges, labels)
    return BaselineResult(graph, [] if graph else ["assembled graph failed validation"])


# --- nodes ----------------------------------------------------------------------------


def _find_regions(ink: np.ndarray) -> list[Region]:
    """Enclosed background regions (not connected to the border) with ink inside: shapes
    with text. Letter counters ("o", "e") and hollow arrowheads enclose no ink."""
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        (~ink).astype(np.uint8), connectivity=4
    )
    border = set(
        np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]])).tolist()
    )
    regions = []
    for index in range(1, count):
        x, y, w, h, area = stats[index]
        if index in border or area < 40 or area > 0.6 * ink.size or min(w, h) < 6:
            continue
        sub = (labels[y : y + h, x : x + w] == index).astype(np.uint8)
        contours, _ = cv2.findContours(sub, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contour = max(contours, key=cv2.contourArea)
        filled = np.zeros_like(sub)
        cv2.drawContours(filled, [contour], -1, 1, thickness=cv2.FILLED)
        if (filled.astype(bool) & ink[y : y + h, x : x + w]).sum() < 8:
            continue
        fill = np.zeros(ink.shape, bool)
        fill[y : y + h, x : x + w] = filled.astype(bool)
        vertices = len(cv2.approxPolyDP(contour, 0.04 * cv2.arcLength(contour, True), True))
        regions.append(Region(index, fill, (int(x), int(y), int(x + w), int(y + h)), [], vertices))
    return regions


def _read_group_label(
    gray: np.ndarray, ink: np.ndarray, region: Region, regions: list[Region], scale: float
) -> list[TextLine]:
    # A group's label sits in the band along its top edge, outside the shapes it contains.
    children = np.zeros(ink.shape, bool)
    for other in regions:
        if other.parent == regions.index(region):
            children |= other.fill
    x0, y0, x1, y1 = region.bbox
    band_height = round(2.5 * scale) + GROUP_MARGIN
    band = np.zeros(ink.shape, bool)
    band[y0 : y0 + band_height, x0:x1] = True
    keep = region.fill & band & ~_dilate(children, 3)
    # Edges running through the label band span it top to bottom; letters never do.
    _, parts, stats, _ = cv2.connectedComponentsWithStats(
        (ink & keep).astype(np.uint8), connectivity=8
    )
    spanning = stats[:, cv2.CC_STAT_HEIGHT] >= 0.8 * band_height
    spanning[0] = False
    keep &= ~_dilate(spanning[parts], 1)
    lines = sorted(read_region(gray, ink, keep, sparse=True), key=lambda t: t.y0)
    if not lines:
        return []
    top = lines[0]
    row = sorted(
        (t for t in lines if abs(t.center[1] - top.center[1]) < 0.5 * top.height),
        key=lambda t: t.x0,
    )
    return [
        TextLine(
            " ".join(t.text for t in row),
            row[0].x0,
            min(t.y0 for t in row),
            row[-1].x1,
            max(t.y1 for t in row),
            min(t.confidence for t in row),
        )
    ]


def _dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * radius + 1, 2 * radius + 1))
    return cv2.dilate(mask.astype(np.uint8), kernel).astype(bool)


def _add_filled_groups(rgb: np.ndarray, regions: list[Region]) -> list[Region]:
    """Filled group boxes: a coloured area that encloses shapes. Edges running through a
    group cut its interior into pieces, so the enclosed-region test alone misses it; with
    thin strokes eroded away, the fill is one area again. Pieces of the interior (regions
    touching the group's border) are not nodes."""
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    background = np.median(border, axis=0)
    painted = (np.abs(rgb.astype(np.int16) - background).max(axis=2) > FILL_CONTRAST).astype(
        np.uint8
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * STROKE_ERODE + 1,) * 2)
    fills = cv2.erode(painted, kernel)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(fills, connectivity=8)
    groups: list[Region] = []
    for index in range(1, count):
        x, y, w, h, _ = stats[index]
        box = (
            int(x - STROKE_ERODE),
            int(y - STROKE_ERODE),
            int(x + w + STROKE_ERODE),
            int(y + h + STROKE_ERODE),
        )
        # A group surrounds its members with a margin; a filled node's own interior fits
        # its fill within a few pixels.
        members = [r for r in regions if _box_inside(r.bbox, box, slack=GROUP_MARGIN)]
        area = (box[2] - box[0]) * (box[3] - box[1])
        if not members or area < 1.5 * max(_area(r.bbox) for r in members):
            continue
        fill = cv2.dilate((labels == index).astype(np.uint8), kernel).astype(bool)
        groups.append(Region(-index, fill, box, [], 4, is_group=True, filled_group=True))
    if not groups:
        return regions
    kept = []
    for region in regions:
        pieces = [
            g
            for g in groups
            if _box_inside(region.bbox, g.bbox, slack=-1) and _touches_edge(region.bbox, g.bbox)
        ]
        if not pieces:
            kept.append(region)
    return kept + groups


def _box_inside(
    inner: tuple[int, int, int, int], outer: tuple[int, int, int, int], *, slack: int
) -> bool:
    """inner lies within outer, at least ``slack`` px from its edges (negative: may overlap)."""
    return (
        inner[0] >= outer[0] + slack
        and inner[1] >= outer[1] + slack
        and inner[2] <= outer[2] - slack
        and inner[3] <= outer[3] - slack
    )


def _area(box: tuple[int, int, int, int]) -> int:
    return (box[2] - box[0]) * (box[3] - box[1])


def _touches_edge(inner: tuple[int, int, int, int], outer: tuple[int, int, int, int]) -> bool:
    near = 2 * STROKE_ERODE + 2
    return (
        min(inner[0] - outer[0], inner[1] - outer[1], outer[2] - inner[2], outer[3] - inner[3])
        <= near
    )


def _assign_groups(regions: list[Region]) -> None:
    """A region enclosing another region's box is a group; parents = smallest enclosing group."""

    def inside(inner: Region, outer: Region) -> bool:
        a, b = inner.bbox, outer.bbox
        return (
            inner is not outer and a[0] >= b[0] and a[1] >= b[1] and a[2] <= b[2] and a[3] <= b[3]
        )

    for region in regions:
        region.is_group = region.filled_group or any(inside(other, region) for other in regions)
        region.parent = None
    for region in regions:
        enclosing = [g for g in regions if g.is_group and inside(region, g)]
        if enclosing:
            smallest = min(
                enclosing, key=lambda g: (g.bbox[2] - g.bbox[0]) * (g.bbox[3] - g.bbox[1])
            )
            region.parent = regions.index(smallest)


# --- edges ----------------------------------------------------------------------------


def _stroke_mask(
    ink: np.ndarray, regions: list[Region], free_text: list[TextLine], scale: float
) -> np.ndarray:
    """Ink minus shapes (with their outlines), group borders and free text."""
    margin = max(2, round(scale * 0.25))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * margin + 1, 2 * margin + 1))
    erase = np.zeros(ink.shape, np.uint8)
    for region in regions:
        if region.is_group:  # only the border band, never the contents
            contours, _ = cv2.findContours(
                region.fill.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
            )
            cv2.drawContours(erase, contours, -1, 1, thickness=2 * margin + 1)
        else:
            erase |= cv2.dilate(region.fill.astype(np.uint8), kernel)
    for line in free_text:
        erase[max(0, line.y0 - 1) : line.y1 + 2, max(0, line.x0 - 1) : line.x1 + 2] = 1
    strokes = (ink & ~erase.astype(bool)).astype(np.uint8)
    # Close the small gaps left where edges cross a group border.
    return cv2.morphologyEx(
        strokes, cv2.MORPH_CLOSE, np.ones((margin + 2, margin + 2), np.uint8)
    ).astype(bool)


@dataclass
class _Edge:
    source: Region
    target: Region
    component: int


def _find_edges(strokes: np.ndarray, nodes: list[Region], scale: float) -> list[_Edge]:
    count, components = cv2.connectedComponents(strokes.astype(np.uint8), connectivity=8)
    margin = max(2, round(scale * 0.25))
    reach = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * (margin + 3) + 1,) * 2)
    zones = [cv2.dilate(n.fill.astype(np.uint8), reach).astype(bool) for n in nodes]
    radius = max(4.0, scale)
    edges: list[_Edge] = []
    sizes = np.bincount(components.ravel())
    for component in range(1, count):
        if sizes[component] < scale:  # specks
            continue
        pixels = components == component
        contacts = []
        for node, zone in zip(nodes, zones, strict=True):
            touching = pixels & zone
            if touching.any():
                ys, xs = np.nonzero(touching)
                contacts.append((node, _ink_near(pixels, xs.mean(), ys.mean(), radius)))
        if len(contacts) < 2:
            continue
        thinnest = min(mass for _, mass in contacts)
        heads = [n for n, mass in contacts if mass >= HEAD_RATIO * thinnest]
        tails = [n for n, mass in contacts if mass < HEAD_RATIO * thinnest]
        if not heads:  # no visible arrowhead: assume the flow reads left→right / top→bottom
            a, b = contacts[0][0], contacts[1][0]
            dx, dy = b.center[0] - a.center[0], b.center[1] - a.center[1]
            forward = dx > 0 if abs(dx) > abs(dy) else dy > 0
            tails, heads = ([a], [b]) if forward else ([b], [a])
        edges.extend(_Edge(t, h, component) for t in tails for h in heads if t is not h)
    unique: dict[tuple[str, str], _Edge] = {}
    for edge in edges:
        unique.setdefault((edge.source.node_id, edge.target.node_id), edge)
    return list(unique.values())


def _ink_near(pixels: np.ndarray, x: float, y: float, radius: float) -> int:
    h, w = pixels.shape
    x0, x1 = max(0, int(x - radius)), min(w, int(x + radius) + 1)
    y0, y1 = max(0, int(y - radius)), min(h, int(y + radius) + 1)
    return int(pixels[y0:y1, x0:x1].sum())


def _label_edges(
    edges: list[_Edge], free_text: list[TextLine], strokes: np.ndarray, scale: float
) -> dict[int, str]:
    """Free text within ~2 text heights of a stroke labels the nearest edge of that stroke."""
    if not edges:
        return {}
    distance = cv2.distanceTransform((~strokes).astype(np.uint8), cv2.DIST_L2, 3)
    labels: dict[int, str] = {}
    for line in free_text:
        cx, cy = (int(v) for v in line.center)
        box = distance[max(0, line.y0 - 1) : line.y1 + 2, max(0, line.x0 - 1) : line.x1 + 2]
        if box.size == 0 or box.min() > 2 * scale:
            continue

        index = min(
            range(len(edges)),
            key=lambda i: _point_segment(cx, cy, edges[i].source.center, edges[i].target.center),
        )
        labels.setdefault(index, line.text)
    return labels


def _point_segment(px: float, py: float, a: tuple[float, float], b: tuple[float, float]) -> float:
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = (
        0.0
        if dx == dy == 0
        else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    )
    return float(np.hypot(px - (ax + t * dx), py - (ay + t * dy)))


# --- assembly -------------------------------------------------------------------------


def _assemble(
    regions: list[Region], edges: list[_Edge], edge_labels: dict[int, str]
) -> DiagramGraph | None:
    has_in = {e.target.node_id for e in edges}
    has_out = {e.source.node_id for e in edges}

    def node_type(region: Region) -> str:
        if region.is_group:
            return "group"
        if region.vertices == 4 and _is_diamond(region):
            return "decision"
        if region.vertices == 6:
            return "fusion"
        if edges and region.node_id not in has_in:
            return "input"
        if edges and region.node_id not in has_out:
            return "output"
        return "module"

    ordered = sorted(regions, key=lambda r: int(r.node_id[1:]))
    words = " ".join(r.label for r in regions).casefold().split()
    payload = {
        "schema_version": "2.0",
        "diagram_type": _diagram_type(words, any(node_type(r) == "decision" for r in regions)),
        "nodes": [
            {
                "id": r.node_id,
                "label": r.label,
                "type": node_type(r),
                "group_id": regions[r.parent].node_id if r.parent is not None else None,
            }
            for r in ordered
        ],
        "edges": [
            {
                "source": e.source.node_id,
                "target": e.target.node_id,
                "relation": "flows_to",
                "label": edge_labels.get(i),
            }
            for i, e in enumerate(edges)
        ],
    }
    try:
        return DiagramGraph.model_validate(payload)
    except ValidationError:
        return None


def _is_diamond(region: Region) -> bool:
    """A 4-gon whose area is about half its bounding box (a rectangle fills it)."""
    x0, y0, x1, y1 = region.bbox
    return region.fill.sum() < 0.7 * (x1 - x0) * (y1 - y0)


def _diagram_type(words: list[str], has_decision: bool) -> str:
    votes = Counter()
    for diagram_type, keywords in TYPE_KEYWORDS.items():
        vocabulary = set(keywords.split())
        votes[diagram_type] = sum(w.strip(".,:;()") in vocabulary for w in words)
    if has_decision:
        votes["flowchart"] += 2
    best, score = votes.most_common(1)[0]
    return best if score > 0 else "other"
