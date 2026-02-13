from pathlib import Path

from madd.cli import build_parser


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
