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
    from convert import convert
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.prompts import MessagesPlaceholder
    import sys
    from langchain_core.prompts import ChatPromptTemplate
    from typing_extensions import TypedDict
    from langchain_core.messages import ToolMessage
    from langchain_core.runnables import RunnableLambda
    from langgraph.checkpoint.memory import MemorySaver
    from tools.find_protocols import find_protocols
    from db_config import execute_query, create_connection, fetch_query


    state_file = 'src/app_state.json'
    default_state = init_json()
    json_state = load_state(state_file) if os.path.exists(state_file) else default_state

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
                " Use the file {PCAP}."
            ),
            MessagesPlaceholder("messages"),
        ]
    )


    connection = create_connection()
    this_pcap_id = 0
    if connection:
        insert_sql_query = """
        INSERT INTO pcaps (pcap_filepath, csv_filepath) 
        VALUES (%s, %s)
        RETURNING pcap_id;
        """
        this_pcap_id = execute_query(connection, insert_sql_query, (true_PCAP_path, PCAP_File.name))

        connection.close()


    tools = [find_protocols]

    base = os.path.splitext(PCAP_File.name)
    base_pcap = base[0]

    llm_with_tools = llm.bind_tools(tools)

    packto_runnable = primary_assistant_prompt | llm_with_tools

    """
    Define graph state
    This makes it so that every message will be in a list
    and all of those messages will be received to every node
    in the graph when it is called. Nodes are basically just 
    functions. So those functions will be called and they will 
    receive messages state as input
    """
    class AgentState(TypedDict):
        messages: Annotated[list, add_messages]#Annotated[Sequence[BaseMessage], operator.add]
        PCAP: str

    #Node to see if we need to keep calling tools to answer the question
    def should_continue(state):
        return "continue" if state["messages"][-1].tool_calls else "end"

    #call the model using the previous messages
    def call_model(state, config):
        response = packto_runnable.invoke(state)
        return {"messages": [response]}

    #execute the tool
    def _invoke_tool(tool_call):
        tool = {tool.name: tool for tool in tools}[tool_call["name"]]
        return ToolMessage(tool.invoke(tool_call["args"]), tool_call_id=tool_call["id"])

    tool_executor = RunnableLambda(_invoke_tool)

    #Decide which tool is best
    def call_tools(state):
        last_message = state["messages"][-1]
        return {"messages": tool_executor.batch(last_message.tool_calls)}

    memory = MemorySaver()

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("action", call_tools)
    workflow.set_entry_point("agent")

    """
    Conditional edge so that every time the agent is finished,
    we check if it should continue. If we should, call more tools.
    If not, end.
    """
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "continue": "action",
            "end": END,
        },
    )
    #Allow a connection between action and agent so that the model can call tools
    workflow.add_edge("action", "agent")
    graph = workflow.compile(checkpointer=memory)
    input = {
        "messages": [HumanMessage("What protocols do you see in the trace?")],
        "PCAP": true_PCAP_path,
    }
    config = {"configurable": {"thread_id": str(this_pcap_id)}}

    result = graph.invoke(input, config)

    answer = result['messages'][-1].content

    print("ANSWER:", answer)

init_pcap("uploads/TestPcap.pcapng")



"""
NEXT STEPS:
    - Add memory
    - Add prompting to improve responses
"""