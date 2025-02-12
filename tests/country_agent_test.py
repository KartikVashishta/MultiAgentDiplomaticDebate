import pytest
from agentscope.message import Msg
from agentscope import init
from src.agents.country_agent import CountryAgent
from src.utils.utils import BASIC_MODEL_CONFIG

@pytest.fixture(scope="session", autouse=True)
def setup_agentscope():
    
    init(
        model_configs={
            "model_type": "openai_chat",  
            "model_name": "gpt-4o-mini",   
            "config_name": "openai_config",
        }
    )

@pytest.fixture
def usa_agent():
    return CountryAgent(country_name="United States")

@pytest.fixture
def china_agent():
    return CountryAgent(country_name="China")

def test_country_agent_initialization(usa_agent):
    assert usa_agent.country_name == "United States"
    assert len(usa_agent.memory_stream.general_memory.get_memory()) == 1  
    assert len(usa_agent.memory_stream.debate_memory.get_memory()) == 0
    assert len(usa_agent.memory_stream.strategy_memory.get_memory()) == 0

def test_country_agent_observe_and_reply(usa_agent):
    china_message = Msg(
        name="China",
        content="We express serious concern over recent military activities in the South China Sea.",
        role="assistant"
    )
    
    usa_agent.observe(china_message)
    assert len(usa_agent.memory_stream.debate_memory.get_memory()) == 1
    
    # Test reply
    response = usa_agent(china_message)
    
    assert response.name == "United States"
    assert isinstance(response.content, str)
    assert "thought" in response.metadata

def test_country_agent_diplomatic_validation(usa_agent):

    provocative_msg = Msg(
        name="North Korea",
        content="Your military exercises are a direct threat to our sovereignty!",
        role="assistant"
    )
    
    response = usa_agent(provocative_msg)
    print(f"\nProvocative message: {provocative_msg.content}")
    print(f"Diplomatic response: {response.content}")
    print(f"Validation notes: {response.metadata.get('validation_notes', [])}")
    
    assert response.name == "United States"
    assert isinstance(response.content, str)
    # assert "validation_notes" in response.metadata

def test_country_agent_memory_integration(usa_agent, china_agent):
    
    msg1 = Msg(
        name="China",
        content="We propose new trade negotiations to address the current tariffs.",
        role="assistant"
    )
    
    response1 = usa_agent(msg1)
    print(f"\nFirst exchange:")
    print(f"China: {msg1.content}")
    print(f"USA: {response1.content}")
    
    msg2 = Msg(
        name="China",
        content=f"Regarding your response about {response1.content[:50]}..., we suggest concrete steps.",
        role="assistant"
    )
    
    response2 = usa_agent(msg2)
    print(f"\nSecond exchange:")
    print(f"China: {msg2.content}")
    print(f"USA: {response2.content}")
    
    # Verify memory retention
    assert len(usa_agent.memory_stream.debate_memory.get_memory()) == 2
    assert len(usa_agent.memory_stream.strategy_memory.get_memory()) > 0

def test_country_agent_prompt_construction(usa_agent):
    
    msg = Msg(
        name="Russia",
        content="We demand immediate withdrawal of sanctions.",
        role="assistant"
    )
    
    messages = usa_agent._construct_prompt(msg)
    assert isinstance(messages, list)
    assert all(isinstance(m, dict) for m in messages)
    assert all("role" in m and "content" in m for m in messages)
    
    print("\nConstructed prompt:")
    for m in messages:
        print(f"\nRole: {m['role']}")
        print(f"Content preview: {m['content'][:100]}...")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])