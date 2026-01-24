import argparse
from pathlib import Path


def main():
    """Run the MADD CLI."""
    parser = argparse.ArgumentParser(
        prog="madd",
        description="Multi-Agent Diplomatic Debate - LangGraph simulation"
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
        help="Override max rounds from scenario"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory for output files"
    )
    
    args = parser.parse_args()
    
    # TODO: Implement graph execution
    print(f"Would run scenario: {args.scenario}")
    print(f"Rounds: {args.rounds or 'from scenario'}")
    print(f"Output: {args.output_dir}")


if __name__ == "__main__":
    main()
