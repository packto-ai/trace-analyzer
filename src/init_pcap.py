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
    from tools.analyze_packet import analyze_packet
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

    questions = ["What are all the protocols that you see in the trace?",
                 "What is the subnet the packet trace was operating on",
                 "Give me a list of all the nodes on the network and their corresponding IP addresses",
                 "Tell me about packet number 7",
                 ]

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

    init_qa = {"chat": []}

    for question in questions:
        input = {
            "messages": [HumanMessage(question)],
            "PCAP": true_PCAP_path,
            "external_context": json_state['proto_store']
        }
        config = {"configurable": {"thread_id": str(this_pcap_id)}}

        result = graph.invoke(input, config)

        answer = result['messages'][-1].content

        human_question = {
            "sender": "Human",
            "message": question
        }
        ai_answer = {
            "sender": "Packto",
            "message": answer
        }
        init_qa["chat"].append(human_question)
        init_qa["chat"].append(ai_answer)
        

    app_state = graph.get_state(config).values

    json_app_state = convert_to_json(app_state)
    init_qa_json = json.dumps(init_qa)

    connection = create_connection()
    if connection:
        update_query = """
        UPDATE pcaps
        SET graph_state = %s,
            init_qa = %s
        WHERE pcap_id = %s;
        """
        execute_query(connection, update_query, (json_app_state, init_qa_json, this_pcap_id))

init_pcap("Trace.pcapng")



"""
NEXT STEPS:
    - Get frontend working!
    - Add another tool and see if the reasoner can use both to answer questions
    - Add Ragging up front so that the vectors can be made before the user asks questions
"""

"""
Issues:
    - When I ask, tell me about the protocols in the trace, it just gives me a summary of every protocol i put in the external context, not specifically the ones in the trace
"""

"""
Tools to make:
    - Analyze a specific packet
    - Asset discovery (find the endpoints of the network given a packet trace)
    - Check if there is a broken link (a packet is sent but never received, only one side to a two-sided convo)
    - Check if there are connections with a large number of retries
    - Is there a pattern to requests that are happening at a regular interval? (if so, it could be a security threat. Someone is spying on the network)
    - Given a set of constraints, are any packets getting past those constraints?
"""