from typing_extensions import TypedDict
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableLambda
from langgraph.prebuilt import ToolNode
import pyshark
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

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant"),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ]
)

class ProtocolsInput(BaseModel):
    PCAP: str = Field(description="should be a filepath that ends in .pcap or .pcapng")

# @tool("find-protocols", args_schema=ProtocolsInput, return_direct=True)
@tool
def find_protocols(PCAP: str):
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
        protocols.append(protocol)

    # count = 1
    # for i in protocols:
    #     print(f"Packet {count} ", i)
    #     count += 1
    
    #return f"The protocols in the trace are: {', '.join(protocols)}"
    return {', '.join(protocols)}
protocol_tool = StructuredTool.from_function(
    func=find_protocols,
    name="Protocols",
    description="find protocols in the trace",
    handle_tool_error=True,
    args_schema=ProtocolsInput,
    return_direct=True,
)

def find_protocols_error(s: str):
    raise ToolException("The tool is not working")


tools = [find_protocols]
#environment variables
load_dotenv(dotenv_path="C:/Users/sarta/BigProjects/packto.ai/keys.env")
mistral_key = os.getenv('MISTRAL_API_KEY')

llm = ChatMistralAI(model="mistral-large-latest", temperature=0)

llm_tools = llm.bind_tools(tools=tools)
query = "What protocols are in the following trace: TestPcap.pcapng"



agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

result = agent_executor.invoke(
    {
        "input": (
            "what protocols are in the packet trace TestPcap.pcapng"
        )
    }
)
print(result["output"])