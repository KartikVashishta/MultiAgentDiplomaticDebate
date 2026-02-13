import argparse
import re
import textwrap
import traceback
from dataclasses import dataclass
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from madd.core.graph import build_graph
from madd.core.scenario import Scenario, load_scenario_from_text
from madd.core.state import create_initial_state
from madd.stores.run_store import create_run_dir, save_all_outputs

ALLOWED_EXTENSIONS = {
    "json",
    "md",
    "txt",
    "yml",
    "yaml",
}


@dataclass
class DebateRunResult:
    scenario: Scenario
    run_dir: Path
    outputs: dict[str, Path]


def run_scenario_from_yaml_text(
    yaml_text: str,
    *,
    output_dir: Path | str = "output",
    rounds: int | None = None,
) -> DebateRunResult:
    scenario = load_scenario_from_text(yaml_text)
    if rounds is not None:
        scenario = scenario.model_copy(update={"max_rounds": rounds})

    initial_state = create_initial_state(scenario)
    graph = build_graph()
    final_state = None
    for event in graph.stream(initial_state, stream_mode="values"):
        final_state = event

    if final_state is None:
        raise RuntimeError("Debate run did not produce a final state")

    run_dir = create_run_dir(str(output_dir))
    outputs = save_all_outputs(final_state, run_dir)
    return DebateRunResult(scenario=scenario, run_dir=run_dir, outputs=outputs)


def _read_preview(path: Path, *, limit: int = 8000) -> str:
    if not path.exists():
        return "Missing output file."
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return "Unable to read output file."
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 20].rstrip() + "\n\n... (truncated)"


def _file_link(filename: str) -> bool:
    return bool(re.fullmatch(r"[a-zA-Z0-9._-]+", filename))


def _safe_filename(filename: str) -> bool:
    return bool(re.fullmatch(r"^[^/\\]+\.?[^\x00/\\]*$", filename))


def _html_template(title: str, body: str) -> str:
    return f"""<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <title>{escape(title)}</title>
    <style>
      body {{
        font-family: "Inter", "Segoe UI", system-ui, -apple-system, sans-serif;
        background: #f4f6fc;
        margin: 0;
        color: #15213f;
      }}
      .shell {{
        max-width: 980px;
        margin: 0 auto;
        padding: 24px 16px 42px;
      }}
      h1 {{
        margin: 0 0 12px;
      }}
      .card {{
        background: #ffffff;
        border: 1px solid #d6dded;
        border-radius: 12px;
        padding: 16px;
        margin: 12px 0 16px;
      }}
      textarea {{
        width: 100%;
        height: 300px;
        border-radius: 10px;
        border: 1px solid #cad3eb;
        padding: 12px;
        font-family: "SFMono-Regular", Menlo, Consolas, monospace;
      }}
      .row {{
        display: flex;
        gap: 10px;
        align-items: center;
        flex-wrap: wrap;
      }}
      input[type=\"number\"] {{
        width: 120px;
        padding: 8px;
        border: 1px solid #cad3eb;
        border-radius: 8px;
      }}
      button {{
        padding: 10px 14px;
        border: 0;
        background: #1f3c88;
        color: white;
        border-radius: 8px;
        font-weight: 600;
        cursor: pointer;
      }}
      pre {{
        background: #1e2438;
        color: #e8ebff;
        border-radius: 10px;
        padding: 14px;
        overflow: auto;
      }}
      .ok {{ color: #147d5e; }}
      .err {{ color: #c0392b; }}
      .pill {{
        display: inline-block;
        background: #e8eefb;
        border-radius: 999px;
        padding: 4px 10px;
        margin-right: 8px;
      }}
      .files {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
        gap: 8px;
      }}
      a {{
        color: #1f3c88;
      }}
    </style>
  </head>
  <body>
    <div class=\"shell\">
      {body}
    </div>
  </body>
</html>"""


def _build_index_page() -> str:
    sample_yaml = textwrap.dedent(
        """\
        name: "Greenland Security and Critical Minerals"
        description: "Test scenario for UI verification."
        countries:
          - Denmark
          - United States
        max_rounds: 2

        agenda:
          - topic: "Defense access and updated basing arrangements"
            description: "Clarifying presence and review cycles."
            priority: 1
          - topic: "Environmental safeguards"
            description: "Monitoring, data transparency, and remediation rules."
            priority: 2
        """
    ).strip()

    return _html_template(
        "MADD Scenario Studio",
        f"""
      <h1>MADD Scenario Studio</h1>
      <p>Paste a scenario YAML below and run a full debate iteration.</p>
      <div class=\"card\">
        <form method=\"post\" action=\"/run\">
          <div class=\"row\">
            <label for=\"rounds\"><strong>Override rounds:</strong></label>
            <input id=\"rounds\" name=\"rounds\" type=\"number\" min=\"1\" max=\"10\" />
            <button type=\"submit\">Run Debate</button>
          </div>
          <br />
          <label for=\"scenario\"><strong>Scenario YAML</strong></label>
          <textarea id=\"scenario\" name=\"scenario_yaml\">{escape(sample_yaml)}</textarea>
        </form>
      </div>
      """
    )


def _build_results_page(result: DebateRunResult, *, duration_ms: int | None = None, trace: str = "") -> str:
    output_links = []
    for name, path in result.outputs.items():
        safe_name = escape(str(path.name))
        run_file = f"/runs/{result.run_dir.name}/{safe_name}"
        output_links.append(
            f'<a href="{run_file}" target="_blank" rel="noreferrer">{safe_name} ({escape(name)})</a>'
        )
    if not output_links:
        output_links = ["<span class=\"err\">No files produced.</span>"]

    return _html_template(
        f"Run Complete: {escape(result.scenario.name)}",
        f"""
      <h1>Run Complete</h1>
      <div class=\"card\">
        <div class=\"pill\">Scenario: {escape(result.scenario.name)}</div>
        <div class=\"pill\">Countries: {len(result.scenario.countries)}</div>
        <div class=\"pill\">Rounds: {result.scenario.max_rounds}</div>
        <div class=\"pill\">Run directory: {escape(result.run_dir.as_posix())}</div>
        {f'<div class=\"pill\">Time: {duration_ms}ms</div>' if duration_ms else ''}
      </div>
      <div class=\"card\">
        <h3>Outputs</h3>
        <div class=\"files\">{''.join(f'<div>{link}</div>' for link in output_links)}</div>
      </div>
      <div class=\"card\">
        <h3>Summary Preview</h3>
        <pre>{escape(_read_preview(result.outputs['summary']))}</pre>
      </div>
      {f'<div class=\"card\"><h3>Error Trace</h3><pre>{escape(trace)}</pre></div>' if trace else ''}
      <p><a href=\"/\">Start another run</a></p>
      """
    )


def _build_error_page(message: str, trace: str = "") -> str:
    return _html_template(
        "Run failed",
        f"""
      <h1>Run Failed</h1>
      <div class=\"card err\"><strong>{escape(message)}</strong></div>
      {f'<div class=\"card\"><pre>{escape(trace)}</pre></div>' if trace else ''}
      <p><a href=\"/\">Return to studio</a></p>
      """
    )


def _send_html(handler: BaseHTTPRequestHandler, html: str, *, status: int = 200) -> None:
    body = html.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _send_text_file(handler: BaseHTTPRequestHandler, path: Path) -> None:
    try:
        raw = path.read_bytes()
    except OSError:
        handler.send_response(404)
        handler.end_headers()
        return
    handler.send_response(200)
    handler.send_header("Content-Type", "text/plain; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def _make_handler(output_root: Path):
    output_root = output_root.resolve()

    class DebateStudioHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                _send_html(self, _build_index_page())
                return
            if parsed.path == "/health":
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"ok")
                return
            if parsed.path.startswith("/runs/"):
                run_path = parsed.path.removeprefix("/runs/")
                segments = [segment for segment in run_path.split("/") if segment]
                if len(segments) != 2:
                    self.send_error(404)
                    return
                run_id, filename = segments
                if not _file_link(run_id) or not _safe_filename(filename):
                    self.send_error(400, "Invalid file path")
                    return
                candidate = output_root / run_id / filename
                try:
                    resolved = candidate.resolve()
                except FileNotFoundError:
                    resolved = candidate.resolve()
                if not resolved.is_relative_to(output_root):
                    self.send_error(400, "Invalid file path")
                    return
                if not resolved.exists() or not resolved.is_file():
                    self.send_error(404)
                    return
                if resolved.suffix.lower().lstrip(".") not in ALLOWED_EXTENSIONS:
                    self.send_error(403, "Invalid file extension")
                    return
                _send_text_file(self, resolved)
                return
            self.send_error(404)

        def do_POST(self) -> None:
            if self.path != "/run":
                self.send_error(404)
                return

            content_length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(content_length).decode("utf-8")
            data = parse_qs(body, keep_blank_values=True)
            yaml_text = data.get("scenario_yaml", [""])[0]
            if not yaml_text.strip():
                _send_html(self, _build_error_page("Scenario YAML is required"), status=400)
                return

            rounds_text = data.get("rounds", [""])[0].strip()
            rounds = None
            if rounds_text:
                try:
                    rounds = int(rounds_text)
                except ValueError:
                    _send_html(self, _build_error_page("Invalid value for rounds"), status=400)
                    return

            import time

            start = time.time()
            try:
                result = run_scenario_from_yaml_text(
                    yaml_text,
                    output_dir=output_root,
                    rounds=rounds,
                )
            except Exception as err:
                trace = traceback.format_exc()
                _send_html(self, _build_error_page(f"Run failed: {err}", trace=trace), status=500)
                return
            elapsed_ms = int((time.time() - start) * 1000)
            _send_html(self, _build_results_page(result, duration_ms=elapsed_ms))

        def log_message(self, fmt: str, *args: Any) -> None:
            # Keep server quiet unless explicitly debugging.
            return

    return DebateStudioHandler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="madd-ui",
        description="Run the MADD web UI to draft and execute a scenario",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Base output directory",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open UI in default browser after start",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = _make_handler(args.output_dir.resolve())
    server = HTTPServer((args.host, args.port), handler)

    if args.open:
        import webbrowser

        webbrowser.open(f"http://{args.host}:{args.port}/", new=2)

    print(f"Starting MADD UI on http://{args.host}:{args.port}/")
    print(f"Outputs will be written under: {args.output_dir}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
