import pytest
from src.memory.streams import DiplomaticMemoryStream
from agentscope.message import Msg

@pytest.fixture
def stream():
    return DiplomaticMemoryStream(country_name="United States")

def test_diplomatic_memory_stream_initialization(stream):
    assert isinstance(stream, DiplomaticMemoryStream)
    assert stream.country_name == "United States"

def test_diplomatic_memory_stream_initialization_with_general_memory(stream):
    assert len(stream.general_memory.get_memory()) == 1
    assert len(stream.strategy_memory.get_memory()) == 0
    assert len(stream.debate_memory.get_memory()) == 0

def test_diplomatic_memory_stream_add_message(stream):
    opposition_country_position = Msg(
        name="China", 
        content="Taiwan is considered as a part of China.",
        role="system"
    )
    stream.add(opposition_country_position)
    assert len(stream.debate_memory.get_memory()) == 1
    assert len(stream.strategy_memory.get_memory()) == 1
    assert stream.debate_memory.get_memory()[0] == opposition_country_position
    print(f"Strategy memory: {stream.strategy_memory.get_memory()[0]}")
    assert stream.strategy_memory.get_memory()[0].name == "united_states_strategy"
    assert stream.strategy_memory.get_memory()[0].role == "system"

@pytest.fixture
def stream_with_new_country():
    return DiplomaticMemoryStream(country_name="Germany")

def test_diplomatic_memory_stream_add_message_with_new_country(stream_with_new_country):
    opposition_country_position = Msg(
        name="France", 
        content="Germany is a great country, and we should be friends with them.",
        role="system"
    )
    stream_with_new_country.add(opposition_country_position)
    assert len(stream_with_new_country.debate_memory.get_memory()) == 1
    assert len(stream_with_new_country.strategy_memory.get_memory()) == 1
    assert stream_with_new_country.strategy_memory.get_memory()[0].name == "germany_strategy"
    assert stream_with_new_country.strategy_memory.get_memory()[0].role == "system"

pytest.main([__file__])
