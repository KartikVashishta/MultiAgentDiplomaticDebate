import unittest
from unittest.mock import Mock, patch
import json
import pytest
from typing import List, Dict

from agentscope.message import Msg
from agentscope import init
from agentscope.models import OpenAIChatWrapper
from src.agents.judge_agent import JudgeAgent
from src.utils.utils import BASIC_MODEL_CONFIG

@pytest.fixture(scope="session", autouse=True)
def setup_agentscope():
    """Initialize AgentScope with model configs before any tests run."""
    print("\n=== Initializing AgentScope ===")
    init(
        model_configs={
            "model_type": "openai_chat",  
            "model_name": "gpt-4o-mini",   
            "config_name": "openai_config",
        }
    )  
    print("AgentScope initialized with model config")
    yield

class TestJudgeAgent:
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment before each test method."""
        print("\n=== Setting up Test Case ===")
        self.num_rounds = 3
        self.num_countries = 2
        self.countries = ["USA", "China"]
        
        print(f"Test Parameters:")
        print(f"- Number of rounds: {self.num_rounds}")
        print(f"- Number of countries: {self.num_countries}")
        print(f"- Countries: {', '.join(self.countries)}")
        
        
        self.judge = JudgeAgent(
            num_rounds=self.num_rounds,
            num_countries=self.num_countries,
            model_config=BASIC_MODEL_CONFIG
        )
        print("Initialized JudgeAgent")
        
        
        self.mock_round_response = {
            "round_number": 1,
            "scores": {
                "USA": {
                    "score": 8,
                    "reasoning": "Strong diplomatic approach"
                },
                "China": {
                    "score": 7,
                    "reasoning": "Balanced stance"
                }
            },
            "analysis": {
                "USA": {
                    "diplomatic_effectiveness": 8,
                    "key_points": ["Clear communication", "Strategic focus"],
                    "strategic_alignment": "Well aligned with interests",
                    "thought_process": "Thoughtful and measured"
                },
                "China": {
                    "diplomatic_effectiveness": 7,
                    "key_points": ["Pragmatic approach", "Careful positioning"],
                    "strategic_alignment": "Consistent with objectives",
                    "thought_process": "Strategic and calculated"
                }
            },
            "round_summary": "Productive diplomatic exchange"
        }
        
        self.mock_final_response = {
            "final_scores": {
                "USA": {
                    "score": 8,
                    "key_achievements": ["Consistent diplomacy", "Strong alliances"],
                    "strategic_effectiveness": "Highly effective",
                    "diplomatic_consistency": "Very consistent"
                },
                "China": {
                    "score": 7,
                    "key_achievements": ["Economic cooperation", "Regional influence"],
                    "strategic_effectiveness": "Effective",
                    "diplomatic_consistency": "Mostly consistent"
                }
            },
            "rankings": ["USA", "China"],
            "verdict_summary": "Comprehensive analysis of diplomatic exchanges",  # Must match key in _final_verdict
            "country_performance": {  # Changed from round_progression to country_performance
                "USA": {
                    "round_scores": [8, 7, 8],
                    "strategic_development": "Improving strategy",
                    "key_moments": ["Round 1 alliance", "Round 3 agreement"]
                },
                "China": {
                    "round_scores": [7, 7, 7],
                    "strategic_development": "Consistent approach",
                    "key_moments": ["Round 2 trade deal", "Round 3 cooperation"]
                }
            }
        }
        print("Initialized mock responses")

    def create_country_message(self, country: str, round_num: int) -> Msg:
        """Helper to create test country messages."""
        msg = Msg(
            name=country,
            content=f"Diplomatic statement from {country} for round {round_num}",
            role="assistant",
            metadata={
                "thought": f"Strategic thinking of {country}",
                "key_points": [f"Point 1 from {country}", f"Point 2 from {country}"],
                "strategic_alignment": f"Strategic alignment of {country}"
            }
        )
        print(f"\nCreated message for {country} in round {round_num}:")
        print(f"Content: {msg.content}")
        print(f"Metadata: {json.dumps(msg.metadata, indent=2)}")
        return msg

    def print_memory_state(self):
        """Helper to print current memory state."""
        memory = self.judge.memory.get_memory()
        print("\n=== Current Memory State ===")
        print(f"Total messages in memory: {len(memory)}")
        for i, msg in enumerate(memory):
            print(f"\nMessage {i+1}:")
            print(f"From: {msg.name}")
            print(f"Content: {msg.content}")
            print(f"Metadata: {json.dumps(msg.metadata, indent=2)}")

    @patch.object(OpenAIChatWrapper, '__call__')
    def test_round_evaluation(self, mock_model):
        """Test round-by-round evaluation."""
        print("\n=== Testing Round Evaluation ===")
        
        mock_response = Mock()
        mock_response.text = json.dumps(self.mock_round_response)
        mock_model.return_value = mock_response
        print("Set up mock model response")
        
        print("\nSimulating Round 1:")
        
        
        for country in self.countries:
            msg = self.create_country_message(country, 1)
            result = self.judge(msg)
            assert result is None
            print(f"Added {country}'s message to judge")
        
        self.print_memory_state()
        
        # Get round evaluation
        evaluation = self.judge(None)
        print("\nRound 1 Evaluation:")
        print(f"Content: {evaluation.content}")
        print(f"Metadata: {json.dumps(evaluation.metadata, indent=2)}")
        
        assert evaluation.name == "Judge"
        assert evaluation.metadata["round"] == 1
        print("Evaluation assertions passed")

    @patch.object(OpenAIChatWrapper, '__call__')
    def test_final_verdict(self, mock_model):
        """Test final verdict generation."""
        print("\n=== Testing Final Verdict ===")
        
        # Create Mock responses for each round and final verdict
        mock_responses = []
        
        # Create three round responses
        for _ in range(3):
            round_response = Mock()
            round_response.text = json.dumps(self.mock_round_response)
            mock_responses.append(round_response)
        
        # Create final verdict response
        final_response = Mock()
        final_response.text = json.dumps(self.mock_final_response)
        mock_responses.append(final_response)

        print(f"\nMock Final Response:")
        print(json.dumps(self.mock_final_response, indent=2))
        
        mock_model.side_effect = mock_responses
        
        # Simulate all rounds
        for round_num in range(1, self.num_rounds + 1):
            print(f"\nSimulating Round {round_num}:")
            
            # Add country responses
            for country in self.countries:
                msg = self.create_country_message(country, round_num)
                self.judge(msg)
                print(f"Added {country}'s response for round {round_num}")
            
            # Get round evaluation
            evaluation = self.judge(None)
            print(f"\nRound {round_num} Evaluation:")
            print(json.dumps(evaluation.metadata, indent=2))
        
        # Get final verdict
        final_verdict = self.judge(None)
        print("\nFinal Verdict:")
        print(f"Content: {final_verdict.content}")
        print(f"Metadata: {json.dumps(final_verdict.metadata, indent=2)}")
        
        assert "final_scores" in final_verdict.metadata
        assert "rankings" in final_verdict.metadata
        print("Final verdict assertions passed")

    def test_error_handling(self):
        """Test error cases."""
        print("\n=== Testing Error Handling ===")
        
        # Test insufficient messages for round
        print("\nTesting insufficient messages:")
        msg = self.create_country_message("USA", 1)
        self.judge(msg)
        
        with pytest.raises(ValueError) as exc_info:
            self.judge(None)
        print(f"Error raised as expected: {str(exc_info.value)}")
        
        # Test invalid message format
        print("\nTesting invalid message format:")
        invalid_msg = Msg(
            name="USA",
            content="Invalid message",
            role="assistant"
        )
        self.judge(invalid_msg)
        
        # Print memory state after errors
        self.print_memory_state()

if __name__ == '__main__':
    unittest.main(verbosity=2)