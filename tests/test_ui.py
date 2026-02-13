from pathlib import Path

from madd.core.scenario import load_scenario_from_text
from madd.ui.web import run_scenario_from_yaml_text


def test_load_scenario_from_text():
    scenario = load_scenario_from_text(
        """
name: "UI Case"
description: "Custom test"
countries:
  - North
  - South
max_rounds: 3
"""
    )

    assert scenario.name == "UI Case"
    assert scenario.countries == ["North", "South"]


class _FakeGraph:
    def stream(self, _state, stream_mode):
        yield {"round": 1}


def test_run_scenario_from_yaml_text_supports_round_override(
    monkeypatch,
    tmp_path,
):
    fake_run_dir = tmp_path / "ui_run"

    def fake_build_graph():
        return _FakeGraph()

    def fake_create_run_dir(path: str) -> Path:
        assert path == str(tmp_path)
        return fake_run_dir

    def fake_save_all_outputs(_state, run_dir: Path):
        assert run_dir == fake_run_dir
        return {"summary": run_dir / "summary.md"}

    monkeypatch.setattr("madd.ui.web.build_graph", fake_build_graph)
    monkeypatch.setattr("madd.ui.web.create_run_dir", fake_create_run_dir)
    monkeypatch.setattr("madd.ui.web.save_all_outputs", fake_save_all_outputs)

    result = run_scenario_from_yaml_text(
        """
name: "UI Case"
description: "Custom test"
countries:
  - North
  - South
max_rounds: 3
""",
        output_dir=tmp_path,
        rounds=2,
    )

    assert result.scenario.max_rounds == 2
    assert result.outputs["summary"].name == "summary.md"
    assert result.outputs["summary"].parent == fake_run_dir
