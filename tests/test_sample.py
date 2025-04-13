import json
from ..src.serialize import convert_to_json

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

def test_convert_to_json_success():
    # Create mock messages
    human_msg = HumanMessage(content="Hello!", id="h1", additional_kwargs={}, response_metadata={})
    ai_msg = AIMessage(
        content="Hi there!", id="a1",
        additional_kwargs={}, response_metadata={},
        tool_calls=[], usage_metadata={}
    )
    tool_msg = ToolMessage(content="Tool output", id="t1", tool_call_id="tc1")

    data = {
        "messages": [human_msg, ai_msg, tool_msg],
        "group_id": "group123",
        "PCAPs": ["sample.pcap"],
        "external_context": {"context_key": "context_value"}
    }

    # Run conversion
    json_output = convert_to_json(data)
    parsed = json.loads(json_output)

    # Validate top-level keys
    assert "messages" in parsed
    assert "group_id" in parsed
    assert parsed["group_id"] == "group123"

    # Validate message structure
    assert parsed["messages"][0]["type"] == "human"
    assert parsed["messages"][1]["type"] == "ai"