from typing_extensions import TypedDict
from typing import Annotated, Sequence
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import HumanMessage, SystemMessage, AnyMessage, AIMessage, BaseMessage
from langgraph.prebuilt import ToolNode
import pyshark
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition, create_react_agent
from langchain_core.tools import BaseTool, StructuredTool, tool, ToolException
from pydantic import BaseModel, Field
from langchain_mistralai import ChatMistralAI
from dotenv import load_dotenv
import os
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import MessagesPlaceholder
from langgraph.graph import StateGraph, START, END
import operator


prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant"),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ]
)

# @tool("find-protocols", args_schema=ProtocolsInput, return_direct=True)
@tool
def find_protocols(PCAP: str) -> str:
    """
    Tool to find all the protocols in a given trace.
    It will return a list of strings, where the index in
    the list corresponds to packet number in the PCAP minus 1.
    So index 0 will be packet No. 1.
    """
    protocols = []

    # Load the pcapng file
    capture = pyshark.FileCapture(PCAP)

    for packet in capture:
        protocol = packet.highest_layer
        if (protocol == "DATA"):
            protocol = "UDP"
        if (protocol not in protocols):
            protocols.append(protocol)
    return ', '.join(protocols)


# result = find_protocols.invoke({"PCAP": "TestPcap.pcapng"})

# print(result)

tools = [find_protocols]
#environment variables
load_dotenv(dotenv_path="C:/Users/sarta/BigProjects/packto.ai/keys.env")
mistral_key = os.getenv('MISTRAL_API_KEY')

llm = ChatMistralAI(model="mistral-large-latest", temperature=0)

llm_with_tools = llm.bind_tools(tools=tools)

query = "What protocols are in the given trace: TestPcap.pcapng. Don't repeat traces if they appear up twice, just name me the traces that all appear."

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

def should_continue(state):
    return "continue" if state["messages"][-1].tool_calls else "end"


def call_model(state, config):
    return {"messages": [llm_with_tools.invoke(state["messages"], config=config)]}


def _invoke_tool(tool_call):
    tool = {tool.name: tool for tool in tools}[tool_call["name"]]
    return ToolMessage(tool.invoke(tool_call["args"]), tool_call_id=tool_call["id"])

tool_executor = RunnableLambda(_invoke_tool)

def call_tools(state):
    last_message = state["messages"][-1]
    return {"messages": tool_executor.batch(last_message.tool_calls)}


workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("action", call_tools)
workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "action",
        "end": END,
    },
)
workflow.add_edge("action", "agent")
graph = workflow.compile()

result = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    query
                )
            ],
            "context": "TestPcap.pcapng"
        }
    )

# answer = messages[-1].content
answer = result['messages'][-1].content

print(answer)