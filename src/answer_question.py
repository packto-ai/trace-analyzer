def answer_question(true_PCAP_path, question):
    import os
    import time
    from langchain_mistralai import ChatMistralAI
    from langchain import hub
    from langchain_openai import OpenAIEmbeddings
    from langchain_community.vectorstores import FAISS
    from dotenv import load_dotenv
    from langchain.chains import create_history_aware_retriever
    from langchain_core.prompts import MessagesPlaceholder
    from langchain_core.prompts import ChatPromptTemplate
    from langchain.chains.combine_documents import create_stuff_documents_chain
    from langchain.chains import create_retrieval_chain
    from langchain_community.chat_message_histories import ChatMessageHistory
    from langchain_core.chat_history import BaseChatMessageHistory
    from langchain_core.runnables.history import RunnableWithMessageHistory
    from db_config import create_connection, execute_query, fetch_query
    from serialize import convert_to_json, deserialize_json
    from init_json import init_json, load_state

    state_file = 'src/app_state.json'
    default_state = init_json()
    state = load_state(state_file) if os.path.exists(state_file) else default_state

    #environment variables
    load_dotenv(dotenv_path="C:/Users/sarta/BigProjects/packto.ai/keys.env")
    openai_key = os.getenv('OPENAI_API_KEY')
    langchain_key = os.getenv('LANGCHAIN_API_KEY')
    mistral_key = os.getenv('MISTRAL_API_KEY')
    gemini_key = os.getenv('GOOGLE_API_KEY')

    if gemini_key is None:
        raise ValueError("Did not find MISTRAL_API_KEY. Please ensure it is set in your environment variables or .env file.")

    llm = ChatMistralAI(model="mistral-large-latest", temperature=0)

    #the following variables are constant across everything these don't ever need to change
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large") #GoogleGenerativeAIEmbeddings(model="models/embedding-001")

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
            "Use the following pieces of retrieved context to answer "
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






    chat_store = {}
    this_pcap_id = 0
    init_qa_store = {}
    index = None
    
    connection = create_connection()
    if connection:
        select_query = "SELECT chat_history, csv_filepath, pcap_id, init_qa, vectorstore_path FROM pcaps WHERE pcap_filepath=%s"
        result = fetch_query(connection, select_query, (true_PCAP_path,))
        if (result == []):
            chat_store = {}
        else: 
            chat_store = deserialize_json(result[0][0]) if result[0][0] is not None else {}
            PCAP_File_Path = result[0][1]   
            this_pcap_id = result[0][2]
            init_qa_store = deserialize_json(result[0][3])
            index = result[0][4]
        connection.close()


    external_contexts = state['proto_store']

    while os.path.getsize(PCAP_File_Path) == 0:
            time.sleep(0.1)

    #load in saved data that corresponds to the last_ragged_pcap
    vectorstore = FAISS.load_local(folder_path="vectorstore_index.faiss", embeddings=embeddings, index_name=f"{index}", allow_dangerous_deserialization=True)
    retriever = vectorstore.as_retriever()
    history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_q_prompt)

    qa_chain = create_stuff_documents_chain(llm, qa_prompt)
    rag_chain = create_retrieval_chain(history_aware_retriever, qa_chain)

    #Now we need object to store chat history and updates chat history for the chain
    def get_session_history(session_id: int) -> BaseChatMessageHistory:
        if session_id not in chat_store:
            chat_store[session_id] = ChatMessageHistory()
        return chat_store[session_id]

    history_aware_rag_chain = RunnableWithMessageHistory(
        rag_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )

    generation = history_aware_rag_chain.invoke(
        {"input": question, 
         "external_contexts": external_contexts,
         "init_qa_store": init_qa_store[this_pcap_id]},
        config={
            "configurable":{"session_id": this_pcap_id}
        }, #constructs a session_id key to put in the store
    )

    connection = create_connection()
    if connection:
        update_query = """
        UPDATE pcaps
        SET chat_history = %s
        WHERE pcap_id = %s;
        """

        serialized_chat_store = convert_to_json(chat_store)
        execute_query(connection, update_query, (serialized_chat_store, this_pcap_id))

        connection.close()

    return generation["answer"]