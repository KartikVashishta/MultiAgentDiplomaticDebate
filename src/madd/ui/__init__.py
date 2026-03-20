"""UI helpers for Multi-Agent Diplomatic Debate."""

def run_scenario_from_yaml_text(*args, **kwargs):
    from .web import run_scenario_from_yaml_text as _run_scenario_from_yaml_text

    return _run_scenario_from_yaml_text(*args, **kwargs)

__all__ = ["run_scenario_from_yaml_text"]
