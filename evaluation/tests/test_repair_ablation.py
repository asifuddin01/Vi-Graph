"""evaluation/scripts/repair_ablation.py on the committed final greedy runs (500 samples)."""

from pathlib import Path

import pytest

from evaluation.results import read_results
from evaluation.scripts.repair_ablation import ablation, main, sources

REPORTS = Path(__file__).resolve().parents[1] / "reports"
QLORA = REPORTS / "qwen3vl-2b-qlora-a6000-v1-final-greedy"


def test_validity_and_structure_gain_from_stage_c_and_d() -> None:
    table = ablation(read_results(QLORA))

    valid, p_valid = table["valid"]
    similarity, p_similarity = table["graph_similarity"]
    assert (round(valid.mean_a, 3), round(valid.mean_b, 3)) == (0.728, 0.910)
    assert round(similarity.mean_a, 3) == 0.610 and round(similarity.mean_b, 3) == 0.740
    assert similarity.ci_low > 0 and max(p_valid, p_similarity) < 0.01


def test_final_graphs_by_stage_c_status() -> None:
    counts = {status: n for status, (n, _) in sources(read_results(QLORA)).items()}

    assert counts == {
        "valid_first_attempt": 364,
        "valid_after_retry": 26,
        "repaired": 65,
        "failed": 45,
    }


def test_cli_writes_markdown(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "ablation.md"

    main([str(QLORA), "--out", str(out)])

    assert "| valid | 0.728 | 0.910 |" in out.read_text()
    assert "qwen3vl-2b-qlora-a6000-v1-final-greedy (500 samples)" in capsys.readouterr().out
