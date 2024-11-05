def answer_question(PCAPs, question, graph):
    import sys
    import os
    #ensure we are operating from the project directory, one step above src
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

    #create empty LangGraph which we will put the graph state from database in later
    #graph = config_graph()

    #find which group the PCAPs in this group belong to
    #THIS SHOULD BE CHANGED TO FIND THE GROUP_ID ONLY IF IT IS SAME GROUP_ID FOR EVERY PCAP IN PCAPs ARRAY. 
        #IT IS POSSIBLE FOR A SINGLE PACKET TRACE TO BELONG TO MULTIPLE GROUPS SO THIS WON'T ACTUALLY BE VERY ACCURATE
    connection = create_connection()
    if connection:
        join_query = """
        SELECT group_id
        FROM pcaps
        WHERE pcap_filepath = %s;
        """

    #This needs better error handling in case fetch_query finds nothing
    output = fetch_query(connection, join_query, (PCAPs[0],))
    group_id = output[0][0]

    #get the graph state for this group from the database (which will exist because answer_question will never happen without init_pcap having already happened)
    connection = create_connection()
    loaded_graph_state = None
    output = None
    if connection:
        select_sql_query = """
        SELECT graph_state, chat_history
        FROM pcap_groups
        WHERE group_id = %s
        """
        output = fetch_query(connection, select_sql_query, (group_id,))

        connection.close()


    """
    if we are using this answer_question function that means we have already done init_qa 
    and maybe already have a chat history so we want to load in the previous graph state and chat_history
    for our LangGraph to answer questions using previous history as context and also so that we can use
    the same graph over and over again essentially
    """
    loaded_graph_state = output[0][0]
    chat_history = output[0][1]


    #put chat_history into the correct data type so that we can update it without errors
    if (not chat_history):
        chat_history = {"chat": []}

    #We want to invoke the graph on the question the user asked, using the current PCAP, and using context from the network protocols (changed it to using chat_history as external context)
    input = {
        "messages": [HumanMessage(question)],
        "PCAPs": PCAPs,
        "external_context": chat_history
    }
    config = {"configurable": {"thread_id": str(group_id)}}

    #update the graph state with the state we loaded in above so that we are all current on info
    temp_state = graph.update_state(config, loaded_graph_state)

    #actually use the graph which has the LLM with tools bound to it and decision making capabilities to choose the proper tool
    result = graph.invoke(input, config)

    #result will output a ton of info in a dict. We want to get the answer alone to put in chat history
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

    #update the graph state with the entire result (the dict), not just the answer. Chat history will have just the question and answer
    updated = graph.update_state(config, result)

    #save the graph state so we can put it in the database and load it when they ask another question
    app_state = graph.get_state(config).values
    json_app_state = convert_to_json(app_state)

    #update the database with the updated graph state and chat history for this group
    connection = create_connection()
    if connection:
        update_query = """
        UPDATE pcap_groups
        SET graph_state = %s,
        chat_history = %s
        WHERE group_id = %s;
        """
        execute_query(connection, update_query, (json_app_state, json_chat_history, group_id))

    return answer