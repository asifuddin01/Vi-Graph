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


REPORTS = Path(__file__).resolve().parents[2] / "evaluation" / "reports"


def cell(prefix: str) -> str:
    """The code cell whose first line starts with prefix (sections 9 and 10 are numbered)."""
    sources = ["".join(c["source"]) for c in cells() if c["cell_type"] == "code"]
    (match,) = [s for s in sources if s.startswith(prefix)]
    return match


def test_sections_are_in_order_and_the_intro_lists_them() -> None:
    headings = [
        "".join(c["source"]).split("\n")[0] for c in cells() if c["cell_type"] == "markdown"
    ]
    numbered = [h.split(".")[0].removeprefix("## ") for h in headings if h.startswith("## ")]
    intro = "".join(cells()[0]["source"])

    assert numbered == [str(n) for n in range(1, 11)]
    assert "| 9. Re-evaluation, 4096 tokens |" in intro and "| 10. Resolution ablation |" in intro


def test_reeval_cells_use_4096_tokens() -> None:
    settings = cell("# 9.1")
    assert "MAX_NEW_TOKENS_V2 = 4096" in settings and "-tok4096" in settings


def test_reeval_truncation_counter_matches_the_first_runs() -> None:
    tree = ast.parse(cell("# 9.5"))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef))
    namespace = {"json": json, "gzip": __import__("gzip")}
    exec(compile(ast.Module([function], []), "cell", "exec"), namespace)

    zeroshot = namespace["truncation_by_level"](REPORTS / "qwen3-vl-2b-instruct-zeroshot-s0")
    qlora = namespace["truncation_by_level"](REPORTS / "qwen3vl-2b-qlora-a6000-v1-s0")

    assert zeroshot[4] == (28, 27, 27)  # (n, truncated, failed) at L4 with 2048 tokens
    assert qlora[4] == (28, 11, 10)


def resolution_helpers(eval_dir: Path) -> dict:
    """10.1's functions, run against committed evaluation runs (EVAL_LIMIT 112, 2048 tokens)."""
    tree = ast.parse(cell("# 10.1"))
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    namespace = {
        "json": json,
        "gzip": __import__("gzip"),
        "read_json": lambda path: json.loads(Path(path).read_text(encoding="utf-8")),
        "EXPECTED": 112,
        "EVAL_LIMIT": 112,
        "MAX_NEW_TOKENS_RES": 2048,
        "RUN_NAME": "qwen3vl-2b-qlora-a6000-v1",
        "EVAL_DIR": eval_dir,
        "FIRST_RUN": eval_dir / "qwen3vl-2b-qlora-a6000-v1-s0",
    }
    exec(compile(ast.Module(functions, []), "settings", "exec"), namespace)
    return namespace


def test_resolution_cells_run_the_four_sizes_in_order_at_2048_tokens() -> None:
    settings = cell("# 10.1")
    sources = ["".join(c["source"]) for c in cells() if c["cell_type"] == "code"]
    calls = [s.split("evaluate_size(")[1].split(")")[0] for s in sources if "= evaluate_size(" in s]

    assert "SIZES = [640, 768, 896, 1024]" in settings
    assert "MAX_NEW_TOKENS_RES = 2048" in settings
    assert calls == ["640", "768", "896", "1024"]


def test_resolution_cells_reuse_only_the_matching_896_run() -> None:
    helpers = resolution_helpers(REPORTS)
    first = REPORTS / "qwen3vl-2b-qlora-a6000-v1-s0"

    assert helpers["run_path"](896) == first  # fine-tuned, 896 px, 2048 tokens, 112 samples
    assert helpers["run_path"](640) == REPORTS / "qwen3vl-2b-qlora-a6000-v1-px640-s0"
    assert not helpers["reusable"](REPORTS / "qwen3-vl-2b-instruct-zeroshot-s0", 896)  # no adapter
    assert not helpers["reusable"](REPORTS / "qwen3vl-2b-qlora-a6000-v1-tok4096-s0", 896)
    assert helpers["truncation_by_level"](first)[4] == (28, 11, 10)
