def rag_pcap(true_PCAP_path):
    import os
    import json
    import time
    from langchain_mistralai import ChatMistralAI
    from langchain import hub
    from langchain_community.document_loaders.csv_loader import CSVLoader
    from langchain_community.document_loaders import TextLoader
    from langchain_core.output_parsers import StrOutputParser
    from langchain_openai import OpenAIEmbeddings
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS
    from dotenv import load_dotenv
    from langchain.chains import create_history_aware_retriever
    from langchain_core.prompts import MessagesPlaceholder
    from langchain_core.prompts import ChatPromptTemplate
    from langchain.chains.combine_documents import create_stuff_documents_chain
    from langchain.chains import create_retrieval_chain
    from langchain_community.chat_message_histories import ChatMessageHistory
    from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
    from langchain.schema import messages_from_dict, messages_to_dict
    from langchain.memory import ConversationBufferMemory
    from langchain.chains import ConversationalRetrievalChain, ConversationChain
    from langchain_core.messages import HumanMessage, AIMessage
    from langchain_core.runnables.history import RunnableWithMessageHistory
    from scraper import download_protocols
    import sys
    from convert import convert
    from text_cutter import documentation_iteration
    from db_config import create_connection, execute_query, fetch_query
    from serialize import convert_to_json
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.runnables import RunnablePassthrough
    from init_json import init_json, load_state


    state_file = 'src/app_state.json'
    default_state = init_json()
    state = load_state(state_file) if os.path.exists(state_file) else default_state

    #Uncomment this when running via FastAPI
    # if len(sys.argv) < 2:
    #     raise ValueError("Please provide a file path to convert.")

    # true_PCAP_path = sys.argv[1]

    if not os.path.exists("./NetworkProtocols"):
        download_protocols()

    #environment variables
    load_dotenv(dotenv_path="C:/Users/sarta/BigProjects/packto.ai/keys.env")
    openai_key = os.getenv('OPENAI_API_KEY')
    langchain_key = os.getenv('LANGCHAIN_API_KEY')
    mistral_key = os.getenv('MISTRAL_API_KEY')
    gemini_key = os.getenv('GOOGLE_API_KEY')

    if gemini_key is None:
        raise ValueError("Did not find MISTRAL_API_KEY. Please ensure it is set in your environment variables or .env file.")

    llm = ChatMistralAI(model="mistral-large-latest", temperature=0)

    #Convert pcap to CSV
    PCAP_File = convert(true_PCAP_path)

    base = os.path.splitext(PCAP_File.name)
    base_pcap = base[0]

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

    prompt_structure = hub.pull("rlm/rag-prompt")









    #######
    #The following is RAG on sample pcap
    #######
    #Docs to index for our initial RAG. These will augment the knowledge of our 
    #LLM to know more about pcaps
    #Create PCAP TABLE

    init_qa_store = {} #will store the initial questions we ask about the PCAP. Needs to be kept separate from user questions
    
    external_contexts = [state['proto_store']] #will store other context like the Protocol RAG result

    PCAP_File_Path = PCAP_File.name


    connection = create_connection()
    this_pcap_id = 0
    if connection:
        insert_sql_query = """
        INSERT INTO pcaps (pcap_filepath, csv_filepath) 
        VALUES (%s, %s)
        RETURNING pcap_id;
        """
        this_pcap_id = execute_query(connection, insert_sql_query, (true_PCAP_path, PCAP_File_Path))

        connection.close()

    while os.path.getsize(PCAP_File_Path) == 0:
        time.sleep(0.1)

    loader = CSVLoader(file_path=PCAP_File_Path)  #we might have to make our own file loader for pcap files

    #Load the pdfs in docs_proto = [TextLoader(path).load() for path in Protocol_File_Paths]
    docs_pcap = loader.load()

    if not docs_pcap:
        raise ValueError("No documents were loaded. Please check the CSV file.")

    def clean_metadata(doc):
        for key, value in doc.metadata.items():
            if isinstance(value, list):
                # Convert list to a comma-separated string or handle it as needed
                doc.metadata[key] = ', '.join(value)
            # Add other necessary conversions if needed
        return doc

    # Apply the cleaning function to all documents
    cleaned_documents = [clean_metadata(doc) for doc in docs_pcap]

    #split them line by line, as they are formatted in tcpdump so that each
    #document is a new packet essentially
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(separators=["\n", ",", " "], chunk_size=500, chunk_overlap=200)
    doc_pcap_splits = text_splitter.split_documents(cleaned_documents)

    index = base_pcap
    #create vectorstore
    vectorstore = FAISS.from_documents(doc_pcap_splits, embeddings)
    #vectorstore = FAISS.load_local(folder_path="vectorstore_index.faiss", embeddings=embeddings, index_name=f"{index}", allow_dangerous_deserialization=True)

    retriever = vectorstore.as_retriever()

    vectorstore.save_local(folder_path="vectorstore_index.faiss", index_name=f"{index}")

    #retriever will include the vectorstore and also chat history
    history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_q_prompt)

    qa_chain = create_stuff_documents_chain(llm, qa_prompt)
    rag_chain = create_retrieval_chain(history_aware_retriever, qa_chain)

    #Now we need object to store chat history and updates chat history for the chain

    def get_session_history(session_id: int) -> BaseChatMessageHistory:
        if session_id not in init_qa_store:
            init_qa_store[session_id] = ChatMessageHistory()
        return init_qa_store[session_id]


    history_aware_rag_chain = RunnableWithMessageHistory(
        rag_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )

    # questions = ["What are all the protocols that you see in the trace?",
    #              "For each protocol what IP addresses are communicating with each other?",
    #              "What was the last question I asked?",
    #              "For the TCP protocol please list the pairs of ip addresses communicating with each other",
    #              "For TCP protocol, all packets with the same tuple comprised of source ip, source port, destination ip, destination port, belong to the same session.  Please list all sessions that are active in this trace.",
    #              "Study one of these sessions and draw a picture that represents the communication using mermaid format",
    #              ]
    questions = ["What are all the protocols that you see in the trace?"]

    for query in questions:
        relevant_pcap_docs = retriever.invoke(query)

        def format_docs(relevant_docs):
            return "\n\n".join(doc.page_content for doc in relevant_docs)

        generation = history_aware_rag_chain.invoke(
            {
            "input": query, "context": external_contexts,
            },
            config={"configurable": {"session_id": this_pcap_id}}
        )
    

    connection = create_connection()

    if connection:
        update_query = """
        UPDATE pcaps
        SET ragged_yet = %s,
            vectorstore_path = %s,
            init_qa = %s
        WHERE pcap_id = %s;
        """

        serialized_init_qa_store = convert_to_json(init_qa_store)

        init_qa_store_json = json.dumps(serialized_init_qa_store)
        execute_query(connection, update_query, (True, index, serialized_init_qa_store, this_pcap_id))

        connection.close()


#Uncomment when running in VSCode
true_PCAP_path = "./TestPcap.pcapng"
rag_pcap(true_PCAP_path)