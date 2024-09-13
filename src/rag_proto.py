def rag_protocols():
    #imports and getting logistics set up
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
    from init_json import init_json, save_state, load_state

    state_file = 'src/app_state.json'
    default_state = init_json()
    state = load_state(state_file) if os.path.exists(state_file) else default_state

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

    system_prompt = (
        "You are an expert on Network Protocols and answering questions about packet traces. "
        "Use the following pieces of retrieved context to answer "
        "the question. If you don't know the answer, say that you "
        "don't know."
        "\n\n"
        "{context}"
    )
    #non-history aware. So doesn't need chat_history. For protocol rag
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )







    #######
    #The following is RAG on Protocol Documentation
    #######
    #Docs to index for our initial RAG. These will augment the knowledge of our 
    #LLM to know more about Network Protocols

    proto_chat_store = {}

    Protocol_File_Paths = []

    #split the documents through text_cutter.py
    documentation_iteration()

    directory = 'SplitDocumentation'
    for filename in os.listdir(directory):
        Protocol_File_Paths.append(os.path.join(directory, filename))

    for path in Protocol_File_Paths:
        connection = create_connection()

        if connection:
            insert_sql_query = """
            INSERT INTO protocols (proto_filepath) 
            VALUES (%s);
            """
            execute_query(connection, insert_sql_query, (path,))

            connection.close()

    

    #Load the pdfs in
    docs_proto = [TextLoader(path).load() for path in Protocol_File_Paths]

    docs_proto_list = [item for sublist in docs_proto for item in sublist]

    # Calculate the new chunk size based on the desired token limit (openai only allows 150000 tokens)
    average_tokens_per_chunk = 300
    max_chunks = 150000 // average_tokens_per_chunk
    new_chunk_size = 150000 // max_chunks

    # Update the text splitter with the new chunk size
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(chunk_size=new_chunk_size, chunk_overlap=0)
    doc_proto_splits = text_splitter.split_documents(docs_proto_list)

    embeddings = OpenAIEmbeddings(model="text-embedding-3-large") #GoogleGenerativeAIEmbeddings(model="models/embedding-001")



    #create vectorstore
    vectorstore = FAISS.load_local(folder_path="vectorstore_index.faiss", embeddings=embeddings, index_name=f"ProtoIndex", allow_dangerous_deserialization=True)
    retriever = vectorstore.as_retriever()


    # #retriever will include the vectorstore and also chat history
    # history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_q_prompt)

    qa_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, qa_chain)

    #Now we need object to store chat history and updates chat history for the chain

    question = "Tell me about all the Network Protocols"

    response = rag_chain.invoke({"input": question})

    proto_chat_store[question] = response["answer"]

    state['ragged_proto'] = True
    state['proto_store'] = proto_chat_store

    save_state(state_file, state) #save state at the end of every run of this subprocess