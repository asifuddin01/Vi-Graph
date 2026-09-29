import ast
import json
import re
from pathlib import Path

from training.notebooks.make_notebook import CELLS, NOTEBOOK, render

SECTIONS = [
    "## 1. Setup",
    "## 2. Dataset",
    "## 3. Preprocess",
    "## 4. Model",
    "## 5. Train",
    "## 6. Evaluation",
    "## 7. Save & hand back",
]


def test_committed_notebook_matches_its_generator() -> None:
    assert NOTEBOOK.read_text() == render(), "run: python training/notebooks/make_notebook.py"


def test_sections_come_in_the_agreed_order() -> None:
    headings = [source.splitlines()[0] for kind, source in CELLS if kind == "markdown"]
    found = [next(h for h in headings if h.startswith(section)) for section in SECTIONS]

    assert [headings.index(h) for h in found] == sorted(headings.index(h) for h in found)


def test_every_code_cell_is_valid_python() -> None:
    for kind, source in CELLS:
        if kind != "code":
            continue
        # IPython shell escapes (! and %) become `pass`, keeping the indentation valid.
        python = re.sub(r"^(\s*)[!%].*(\n\s+.*\\?)*$", r"\1pass", source, flags=re.MULTILINE)
        python = "\n".join(
            line for line in python.splitlines() if not line.lstrip().startswith("--")
        )
        ast.parse(python)


def test_notebook_targets_a_t4_and_never_evaluates_on_train() -> None:
    notebook = json.loads(NOTEBOOK.read_text())
    text = "".join("".join(cell["source"]) for cell in notebook["cells"])

    assert notebook["metadata"]["colab"]["gpuType"] == "T4"
    assert '"--split", "test"' in text  # evaluation: held-out test split
    assert "training/configs/qlora_t4.yaml" in text
    assert "package_handback" in text and "Files to give back" in text


def test_notebook_paths_exist_in_the_repo() -> None:
    root = Path(__file__).resolve().parents[2]
    for relative in (
        "training/configs/qlora_t4.yaml",
        "requirements-train.txt",
        "data/splits/synthetic-v1.manifest.json",
    ):
        assert (root / relative).exists(), relative
