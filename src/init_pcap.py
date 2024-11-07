def init_pcap(PCAPs, graph):
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    import json
    from langchain_core.messages import HumanMessage
    from init_json import init_json, load_state
    from convert import convert
    from db_config import execute_query, create_connection, fetch_query
    from serialize import convert_to_json, deserialize_json
    from config_graph import config_graph

    state_file = 'src/app_state.json'
    default_state = init_json()
    json_state = load_state(state_file) if os.path.exists(state_file) else default_state

    #Initial diagnostic and general analysis questions that are answered by the LLM before the user asks any questions
    questions = ["What are all the protocols that you see in the trace?",
                 "What is the subnet the packet trace was operating on",
                 "Give me a list of all the nodes on the network and their corresponding IP addresses",
                 "What active TCP sessions are in the trace",
                ]

    # graph = config_graph()

    connection = create_connection()
    if connection:
        join_query = """
        SELECT group_id
        FROM pcaps
        WHERE pcap_filepath = %s;
        """
    
    output = fetch_query(connection, join_query, (PCAPs[0],))

    print("OUTPUT", output)

    group_id = output[0][0]

    init_qa = {"chat": []}

    print("NSADOJOIHFISAF")

    for question in questions:
        input = {
            "messages": [HumanMessage(question)],
            "PCAPs": PCAPs,
            "external_context": json_state['proto_store']
        }
        config = {"configurable": {"thread_id": str(group_id)}}

        print("I THINK HERE")

        result = graph.invoke(input, config)

        print("DONEZO")

        answer = result['messages'][-1].content

        print("QUESTION", question)
        print("ANSWER", answer)

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
        UPDATE pcap_groups
        SET graph_state = %s,
            init_qa = %s
        WHERE group_id = %s;
        """
        execute_query(connection, update_query, (json_app_state, init_qa_json, group_id))



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