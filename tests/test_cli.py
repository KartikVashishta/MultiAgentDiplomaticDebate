from pathlib import Path
from types import SimpleNamespace

import pytest

from madd.cli import build_parser, main


def test_cli_parser_supports_watch_and_print_summary_flags():
    parser = build_parser()
    parsed = parser.parse_args([
        "--watch",
        "--print-summary",
        "--rounds",
        "2",
        "--output-dir",
        "/tmp/madd_out",
        "examples/scenarios/greenland.yaml",
    ])

    assert parsed.watch is True
    assert parsed.print_summary is True
    assert parsed.rounds == 2
    assert parsed.output_dir == Path("/tmp/madd_out")
    assert parsed.scenario == Path("examples/scenarios/greenland.yaml")


def test_cli_parser_default_output_dir_follows_settings(monkeypatch):
    monkeypatch.setattr(
        "madd.cli.get_settings",
        lambda: SimpleNamespace(output_dir="/tmp/from_settings", debug=False),
    )

    parser = build_parser()
    parsed = parser.parse_args(["examples/scenarios/greenland.yaml"])

    assert parsed.output_dir == Path("/tmp/from_settings")


def test_cli_requires_openai_key_before_loading_scenario(monkeypatch, capsys):
    monkeypatch.setattr(
        "madd.cli.get_settings",
        lambda: SimpleNamespace(openai_api_key="", debug=False, output_dir="output"),
    )
    load_scenario_called = False

    def fake_load_scenario(_path):
        nonlocal load_scenario_called
        load_scenario_called = True
        raise AssertionError("load_scenario should not be reached")

    monkeypatch.setattr("madd.cli.load_scenario", fake_load_scenario)
    monkeypatch.setattr("sys.argv", ["madd", "examples/scenarios/greenland.yaml"])

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 2
    assert load_scenario_called is False
    err = capsys.readouterr().err
    assert "OPENAI_API_KEY is required" in err
