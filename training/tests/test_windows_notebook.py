"""The Windows notebook (training/notebooks/vigraph_qlora_windows.ipynb) is hand-maintained,
not generated; these checks cover what broke on the user's first run."""

import ast
import json
from pathlib import Path

import pytest

NOTEBOOK = Path(__file__).resolve().parents[1] / "notebooks" / "vigraph_qlora_windows.ipynb"


def cells() -> list[dict]:
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))["cells"]


def code(index: int) -> str:
    return "".join(cells()[index]["source"])


def helpers(probe: dict | None, tmp_path: Path) -> dict:
    """image_side() and overrides() from the helpers cell, run against a probe file."""
    probe_file = tmp_path / "memory_probe.json"
    if probe is not None:
        probe_file.write_text(json.dumps(probe))
    tree = ast.parse(code(4))
    wanted = {"probe_result", "image_side", "overrides"}
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    namespace = {
        "json": json,
        "PROBE_FILE": probe_file,
        "RUN_NAME": "run",
        "COMPUTE_DTYPE": "bfloat16",
    }
    exec(compile(ast.Module(functions, []), "helpers", "exec"), namespace)
    return namespace


def test_every_code_cell_parses_and_outputs_are_cleared() -> None:
    for cell in cells():
        if cell["cell_type"] == "code":
            ast.parse("".join(cell["source"]))
            assert cell["outputs"] == [] and cell["execution_count"] is None


def test_vram_cap_is_about_11_gb() -> None:
    settings = code(2)
    value = float(settings.split("VRAM_LIMIT_GB =")[1].split("#")[0])

    assert 10.0 <= value <= 11.0


def test_image_side_before_and_after_the_probe(tmp_path: Path) -> None:
    (tmp_path / "before").mkdir()
    (tmp_path / "after").mkdir()
    fits = {"chosen_image_max_side": 896, "cap_gb": 10.5, "results": []}

    assert helpers(None, tmp_path / "before")["image_side"]() == 1024
    assert helpers(fits, tmp_path / "after")["image_side"]() == 896


def test_a_probe_that_found_nothing_stops_with_a_clear_message(tmp_path: Path) -> None:
    stale = {"chosen_image_max_side": None, "cap_gb": 9.5, "results": []}

    with pytest.raises(RuntimeError, match="Raise VRAM_LIMIT_GB"):
        helpers(stale, tmp_path)["image_side"]()


def test_preprocessing_check_never_passes_a_null_image_size(tmp_path: Path) -> None:
    (tmp_path / "stale").mkdir()
    (tmp_path / "none").mkdir()
    stale = {"chosen_image_max_side": None, "cap_gb": 9.5, "results": []}

    without_size = helpers(stale, tmp_path / "stale")["overrides"](with_image_side=False)
    before_probe = helpers(None, tmp_path / "none")["overrides"]()

    assert json.loads(without_size) == {"run_name": "run", "quantization.compute_dtype": "bfloat16"}
    assert json.loads(before_probe)["data.image_max_side"] == 1024
    assert "overrides(with_image_side=False)" in code(17)
