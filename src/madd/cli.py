import argparse
from pathlib import Path

from madd.core.scenario import load_scenario
from madd.core.state import create_initial_state
from madd.core.graph import build_graph
from madd.stores.run_store import create_run_dir, save_all_outputs


def main():
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
    for event in graph.stream(initial_state, stream_mode="values"):
        final_state = event
    
    if final_state:
        print("\nSaving outputs...")
        run_dir = create_run_dir(str(args.output_dir))
        outputs = save_all_outputs(final_state, run_dir)
        
        print(f"\nOutputs saved to: {run_dir}")
        for name, path in outputs.items():
            print(f"  - {name}: {path.name}")
    
    print("\nDone!")


if __name__ == "__main__":
    main()
