import agentscope
from src.agents.orchestrator import DebateOrchestrator
from src.utils.utils import BASIC_MODEL_CONFIG

def main():
    agentscope.init(model_configs=BASIC_MODEL_CONFIG)
    
    countries = ["United States", "China", "Russia", "Ukraine"]
    problem = "The Legitimacy and Implications of Territorial Annexations in the Modern World."
    orchestrator = DebateOrchestrator(
        countries=countries,
        problem_statement=problem,
        num_rounds=5,
        log_file_path="debate_log.txt"
    )
    orchestrator.run_debate()


if __name__ == "__main__":
    main()