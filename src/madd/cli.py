import argparse
import logging
import sys
import traceback
from pathlib import Path

from madd.core.config import get_settings
from madd.core.graph import build_graph
from madd.core.scenario import load_scenario
from madd.core.state import create_initial_state
from madd.stores.run_store import create_run_dir, save_all_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="madd",
        description="Multi-Agent Diplomatic Debate"
    )
    parser.add_argument(
        "scenario",
        type=Path,
        help="Path to scenario YAML file"
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=None,
        help="Override max rounds"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Base output directory"
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Print per-node progress while the graph runs"
    )
    parser.add_argument(
        "--print-summary",
        action="store_true",
        help="Print final summary to stdout after run"
    )
    return parser


def main():
    settings = get_settings()
    logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)
    parser = build_parser()
    args = parser.parse_args()
    
    print(f"Loading scenario: {args.scenario}")
    scenario = load_scenario(args.scenario)
    
    if args.rounds:
        scenario.max_rounds = args.rounds
    
    print(f"Scenario: {scenario.name}")
    print(f"Countries: {', '.join(scenario.countries)}")
    print(f"Max rounds: {scenario.max_rounds}")
    print()
    
    initial_state = create_initial_state(scenario)
    
    print("Building graph...")
    graph = build_graph()
    
    print("Running debate...\n")
    final_state = None
    try:
        if args.watch:
            running_state = dict(initial_state)
            for update_batch in graph.stream(running_state, stream_mode="updates"):
                for node, update in update_batch.items():
                    if not update:
                        continue
                    if isinstance(update, dict):
                        running_state.update(update)
                    current_round = running_state.get("round", 0)
                    msg_count = len(running_state.get("messages", []))
                    treaty = running_state.get("treaty")
                    treaty_text = len(treaty.clauses) if treaty else 0
                    print(f"[{node}] round={current_round} messages={msg_count} clauses={treaty_text}")
                final_state = running_state
        else:
            for event in graph.stream(initial_state, stream_mode="values"):
                final_state = event
    except Exception as err:
        print(f"Error during debate: {err}", file=sys.stderr)
        traceback.print_exc()
        raise SystemExit(1) from err
    
    if final_state:
        print("\nSaving outputs...")
        run_dir = create_run_dir(str(args.output_dir))
        outputs = save_all_outputs(final_state, run_dir)
        
        print(f"\nOutputs saved to: {run_dir}")
        for name, path in outputs.items():
            print(f"  - {name}: {path.name}")
        if args.print_summary:
            summary_path = outputs.get("summary")
            if summary_path:
                print("\n--- Final Summary ---")
                try:
                    print(Path(summary_path).read_text(encoding="utf-8"))
                except OSError:
                    print("(Unable to read summary file)", file=sys.stderr)
    
    print("\nDone!")


if __name__ == "__main__":
    main()
