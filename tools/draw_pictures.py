from langchain_core.tools import tool
import requests
import os
import scapy
from scapy.all import rdpcap, IP, Ether
from typing import List
from src.db_config import fetch_query, execute_query, create_connection
from langchain_mistralai import ChatMistralAI
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import MessagesPlaceholder
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages, AnyMessage
from typing import Annotated, TypedDict
from langchain_core.runnables import RunnableLambda, Runnable, RunnableConfig
from langchain_core.messages import HumanMessage
from init_json import init_json, load_state

# @tool
def draw_pictures(group_id: int) -> str:
    """
    Tool to draw a diagram of the MAC Addresses on a network
    and how they interact
    """

    state_file = 'src/app_state.json'
    default_state = init_json()
    json_state = load_state(state_file) if os.path.exists(state_file) else default_state

    #Get the currently in use llm and initialize it
    connection = create_connection()
    if connection:
        select_query = "SELECT llm_name, api_key, base_url from llms WHERE in_use=%s"
        model_result = fetch_query(connection, select_query, (True,))
        model = model_result[0][0]
        api_key = model_result[0][1]
        base_url = model_result[0][2]


    if (model == "Mistral"):
        os.environ['MISTRAL_API_KEY'] = api_key
        llm = ChatMistralAI(model="mistral-large-latest", temperature=0)
    elif (model == "Anthropic"):
        os.environ["ANTHROPIC_API_KEY"] = api_key
        llm = ChatAnthropic(model="claude-3-5-sonnet-20240620")
    elif (model == "OpenAI"):
        os.environ['OPENAI_API_KEY'] = api_key
        llm = ChatOpenAI(model="gpt-4o")
    else:
        if not base_url.startswith("http://") and not base_url.startswith("https://"):
            base_url = "http://" + base_url
            print("base_URL", base_url)
        base_url = base_url.replace("localhost", "host.docker.internal")
        if (api_key):
            llm = ChatOpenAI(base_url=base_url, api_key=api_key)
        else:
            llm = ChatOpenAI(base_url=base_url, api_key="not-needed")

    #Get all the mac addresses, tcp_sessions, subnets, etc (All the Metadata about this PCAP group so that it can be fed to the prompt and thus the agent can use them to answer questions)
    connection = create_connection()
    if connection:
        select_query = "SELECT mac_address from macs WHERE group_id=%s"
        mac_result = fetch_query(connection, select_query, (group_id,))
        macs = mac_result[0][0]

    print("MAC ILHANEY", macs)
    print("CHECK 0")

    #This is the prompt we use to tell the LLM its job. We can pass a group of PCAPs in and use anything we want as external_context
    primary_assistant_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                " You are an agent meant to draw a picture of how the MAC Addresses in {macs} connect to each other "
                " Use the additional context of TCP Sessions in {sessions} and {external_context} "
            ),
            MessagesPlaceholder("messages"),
        ]
    )

    #Now let's build the agent
    packto_runnable = primary_assistant_prompt | llm
    print("CHECK 1")

    print("CHECK 2")

    class AgentState(TypedDict):
        messages: Annotated[list[AnyMessage], add_messages]
        macs: List[str]
        sessions: List[str]
        external_context: dict
    print("CHECK 3")
    class Assistant:
        def __init__(self, runnable: Runnable):
            self.runnable = runnable
        def __call__(self, state, config: RunnableConfig):
                while True:
                    configuration = config.get("configurable", {})
                    user_id = configuration.get("user_id", None)
                    state = {**state, "user_info": user_id}
                    result = self.runnable.invoke(state)
                    # Re-prompt if LLM returns an empty response
                    if not result.tool_calls and (
                        not result.content
                        or isinstance(result.content, list)
                        and not result.content[0].get("text")
                    ):
                        messages = state["messages"] + [("user", "Respond with a real output.")]
                        state = {**state, "messages": messages}
                    else:
                        break
                return {"messages": result}
    print("CHECK 4")

    workflow = StateGraph(AgentState)
    print("CHECK 5")
    workflow.add_node("agent", Assistant(packto_runnable))
    print("CHECK 6")
    workflow.add_edge(START, "agent")
    print("CHECK 7")
    #finally make the graph
    graph = workflow.compile()
    print("CHECK 8")
    question = "Please draw a sequence diagram depicting the connection between all the MAC addresses given in Mermaid format"
    input = {
        "messages": [HumanMessage(question)],
        "macs": macs,
        "sessions": [],
        "external_context": json_state['proto_store']
    }
    config = {"configurable": {"thread_id": str(group_id)}}
    print("CHECK 9")
    result = graph.invoke(input, config)
    print("CHECK 10")
    answer = result['messages'][-1].content

    print("ANSWER DRAW PICTURES:\n", answer)

    return answer

"""
Next up, we make a new LangGraph with no tools. We hand it all the info about this group of packet traces
by fetching the macs, ips, subnets, tcp_sessions from the database and using the graph state from the main LangGraph agent
Then we ask the new temporary graph we've made in this tool to draw a mermaid diagram based on all this info
that connects the mac addresses together (we will do this for all the other drawing tools as well but for drawing a diagram that
displays what we want it to). Then get the result of the new graph invocation. Return it as a string. The main agent will
print it out
"""


"""
UNFINISHED
"""