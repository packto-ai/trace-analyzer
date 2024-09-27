def init_pcap(true_PCAP_path):
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    import json
    from langchain_core.messages import ToolMessage, BaseMessage, HumanMessage, AnyMessage, SystemMessage
    from langchain_mistralai import ChatMistralAI
    from scraper import download_protocols
    from typing import Annotated, Sequence, TypedDict
    from langgraph.graph import StateGraph, START, END
    from langgraph.graph.message import add_messages
    from init_json import init_json, load_state
    from dotenv import load_dotenv
    from langchain_openai import OpenAIEmbeddings
    from convert import convert
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.prompts import MessagesPlaceholder
    from typing import Literal
    import sys
    from langchain_core.tools import tool
    from langchain_community.tools.tavily_search import TavilySearchResults
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.runnables import Runnable
    from langchain_aws import ChatBedrock
    import boto3
    from typing_extensions import TypedDict
    from langchain_core.messages import ToolMessage
    from langchain_core.runnables import RunnableLambda
    from langgraph.prebuilt import ToolNode
    import pyshark
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.prebuilt import ToolNode, tools_condition, create_react_agent
    from typing import Optional, Type
    from langchain.agents import initialize_agent
    from langchain.agents import AgentType
    from langchain.callbacks.manager import (
        AsyncCallbackManagerForToolRun,
        CallbackManagerForToolRun,
    )
    import operator
    from langchain.agents import create_tool_calling_agent, AgentExecutor
    from langchain_core.tools import BaseTool, StructuredTool, tool, ToolException
    from langchain_core.runnables import Runnable, RunnableConfig

    from tools.find_protocols import find_protocols


    load_dotenv(dotenv_path="C:/Users/sarta/BigProjects/packto.ai/keys.env")

    PCAP_File = convert(true_PCAP_path)

    #environment variables
    mistral_key = os.getenv('MISTRAL_API_KEY')
    llm = ChatMistralAI(model="mistral-large-latest", temperature=0)

    primary_assistant_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                '''            
                You are an expert on Network Protocols and answering questions about packet traces.
                Use the following pieces of retrieved context to answer
                the question. If you don't know the answer, say that you
                don't know.
                \n\n
                ''',
            ),
            ("placeholder", "{messages}"),
        ]
    )

    #This will be used for creating chat history context on each retrieval
    contextualize_q_system_prompt = (
            "Given a chat history and the latest user question "
            "which might reference context in the chat history, "
            "formulate a standalone question which can be understood "
            "without the chat history. Do NOT answer the question, "
            "just reformulate it if needed and otherwise return it as is."
        )

    #This tells the system to be good at answering a question with a chat history 
    #in mind. MessagesPlaceholder allows us to pass in a list of Messages
    #into the prompt using the "chat_history" input key to provide extra context
    #before a user inputs a question. This helps create the history_aware_retriever
    contextualize_q_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", contextualize_q_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )

    #build functionality for chat history
    system_prompt = (
            "You are an expert on Network Protocols and answering questions about packet traces. "
            "Use the following pieces of retrieved context and the tools at your disposal to answer "
            "the question. If you don't know the answer, say that you "
            "don't know."
            "\n\n"
            "{context}"
        )

    #This helps create the qa_chain whcih will be used with history_aware_retriever
    #to create the rag_chain
    qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
    

    primary_assistant_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful customer support assistant for analyzing packet traces. "
                " Use the provided tools to search for protocols, security threats, and other information to assist the user's queries. "
                " When searching, be persistent. Expand your query bounds if the first search returns no results. "
                " If a search comes up empty, expand your search before giving up."
                f"\n\nCurrent PCAP:\n<PCAP>\n{true_PCAP_path}\n</PCAP>",
            ),
            ("placeholder", "{messages}"),
        ]
    )


    tools = [find_protocols]


    llm_with_tools = llm.bind_tools(tools)

    packto_runnable = primary_assistant_prompt | llm_with_tools

    class AgentState(TypedDict):
        messages: Annotated[Sequence[BaseMessage], operator.add]

    def should_continue(state):
        return "continue" if state["messages"][-1].tool_calls else "end"


    def call_model(state, config):
        # message = llm_with_tools.invoke(state["messages"], config=config)
        # # message.
        print("MESSAGES", state["messages"])
        
        # if hasattr(message, 'tool_calls') and message.tool_calls:
        #     message.tool_calls[0]['args']['PCAP'] = true_PCAP_path
        # message.additional_kwargs['tool_calls'][0]['function']['arguments'] = f'{{"PCAP": "{true_PCAP_path}"}}'
        # # print("call messages: ", [message])
        return {"messages": [llm_with_tools.invoke(state["messages"], config=config)]}


    def _invoke_tool(tool_call):
        tool = {tool.name: tool for tool in tools}[tool_call["name"]]
        # print("tool", tool)
        # print("ToolMessage", ToolMessage(tool.invoke(tool_call["args"]), tool_call_id=tool_call["id"]))
        return ToolMessage(tool.invoke(tool_call["args"]), tool_call_id=tool_call["id"])

    tool_executor = RunnableLambda(_invoke_tool)

    def call_tools(state):
        last_message = state["messages"][-1]
        # print("LAST MESSAGE", last_message)
        # print("messages: ", tool_executor.batch(last_message.tool_calls))
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
                        "What protocols do you see in the trace"
                    ),
                    true_PCAP_path
                ],
            }
        )

    #answer = messages[-1].content
    answer = result['messages'][-1].content

    print("ANSWER: ", answer)

init_pcap("TestPcap.pcapng")



"""
NEXT STEPS:
    - make it answer questions about a PCAP without explicitly mentioning it in the question. Just whatever is passed into init_pcap should be sent as context to the tool
    - Add prompting to improve responses
"""