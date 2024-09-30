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
    from serialize import convert_to_json, deserialize_json
    from config_graph import config_graph

    state_file = 'src/app_state.json'
    default_state = init_json()
    json_state = load_state(state_file) if os.path.exists(state_file) else default_state

    load_dotenv(dotenv_path="C:/Users/sarta/BigProjects/packto.ai/keys.env")

    PCAP_File = convert(true_PCAP_path)

    #environment variables
    mistral_key = os.getenv('MISTRAL_API_KEY')
    llm = ChatMistralAI(model="mistral-large-latest", temperature=0)

    base = os.path.splitext(PCAP_File.name)
    base_pcap = base[0]

    graph = config_graph()

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

    input = {
        "messages": [HumanMessage("What protocols do you see in the trace?"),],
        "PCAP": true_PCAP_path,
        "external_context": json_state['proto_store']
    }
    config = {"configurable": {"thread_id": str(this_pcap_id)}}

    app_state = graph.update_state(config).values

    print("APP STATE", app_state)

    result = graph.invoke(input, config)

    answer = result['messages'][-1].content

    app_state = graph.get_state(config).values

    json_app_state = convert_to_json(app_state)


    connection = create_connection()
    if connection:
        update_query = """
        UPDATE pcaps
        SET graph_state = %s
        WHERE pcap_id = %s;
        """
        execute_query(connection, update_query, (json_app_state, this_pcap_id))

init_pcap("uploads/TestPcap.pcapng")



"""
NEXT STEPS:
    - Write memory to database
    - Add another tool and see if the reasoner can use both to answer questions
    - Add Ragging up front so that the vectors can be made before the user asks questions
"""