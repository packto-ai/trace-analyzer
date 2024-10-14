def answer_question(true_PCAP_path, question):
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    import json
    from langchain_core.messages import HumanMessage
    from init_json import init_json, load_state
    from convert import convert
    from db_config import execute_query, create_connection, fetch_query
    from serialize import convert_to_json
    from config_graph import config_graph

    #Load in the protocol information from json store
    state_file = 'src/app_state.json'
    default_state = init_json()
    json_state = load_state(state_file) if os.path.exists(state_file) else default_state

    PCAP_File = convert(true_PCAP_path)

    base = os.path.splitext(PCAP_File.name)
    base_pcap = base[0]

    graph = config_graph()

    connection = create_connection()
    this_pcap_id = 0
    loaded_graph_state = None
    output = None
    if connection:
        select_sql_query = """
        SELECT pcap_id, graph_state, chat_history
        FROM pcaps
        WHERE pcap_filepath = %s
        """
        output = fetch_query(connection, select_sql_query, (true_PCAP_path,))

        connection.close()


    """
    if we are using this answer_question function that means we have already done init_qa 
    and maybe already have a chat history so we want to load in the previous graph state and chat_history
    for our LangGraph to answer questions using previous history as context and also so that we can use
    the same graph over and over again essentially
    """
    this_pcap_id = output[0][0]
    loaded_graph_state = output[0][1]
    chat_history = output[0][2]

    #put chat_history into the correct data type so that we can update it without errors
    if (not chat_history):
        chat_history = {"chat": []}

    #We want to invoke the graph on the question the user asked, using the current PCAP, and using context from the network protocols (changed it to using chat_history as external context)
    input = {
        "messages": [HumanMessage(question)],
        "PCAP": true_PCAP_path,
        "external_context": chat_history
    }
    config = {"configurable": {"thread_id": str(this_pcap_id)}}

    #update the graph state with the state we loaded in above so that we are all current on info
    temp_state = graph.update_state(config, loaded_graph_state)

    print("TEMP", temp_state)

    result = graph.invoke(input, config)

    answer = result['messages'][-1].content

    #put the chat history in a json-convertible format
    human_question = {
        "sender": "Human",
        "message": question
    }
    ai_answer = {
        "sender": "Packto",
        "message": answer
    }
    chat_history["chat"].append(human_question)
    chat_history["chat"].append(ai_answer)
    #put chat_history in json format
    json_chat_history = json.dumps(chat_history)

    updated = graph.update_state(config, result)

    #save the graph state so we can put it in the database and load it when they ask another question
    app_state = graph.get_state(config).values
    json_app_state = convert_to_json(app_state)

    print("STATE", json_app_state)

    connection = create_connection()
    if connection:
        update_query = """
        UPDATE pcaps
        SET graph_state = %s,
        chat_history = %s
        WHERE pcap_id = %s;
        """
        execute_query(connection, update_query, (json_app_state, json_chat_history, this_pcap_id))

    return answer

answer_question("Trace.pcapng", "Tell me about yourself")
# answer_question("Trace.pcapng", "Tell me about packet number 7")