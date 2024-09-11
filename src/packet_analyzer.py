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

#json state initialization
default_state = {
    'ragged_proto': False, #if we've already ragged against the network docs, we never need to again so need to keep track
    'proto_store': {}
}
state_file = 'src/app_state.json'
if os.path.exists(state_file) and os.path.getsize(state_file) == 0:
    with open(state_file, 'w') as f:
        json.dump(default_state, f, indent=4)
def load_state(state_file):
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            return json.load(f)
    else:
        return { #We want to load all these pieces of state so that when we just want to answer a question about a pcap that has already been ragged
                 #we don't have to go through the entire rag process again, we already have the necessary info about THAT pcap
            'ragged_proto': False, #if we've already ragged against the network docs, we never need to again so need to keep track
            'proto_store': {}
        }   
def save_state(state_file, state):
    with open(state_file, 'w') as f:
        json.dump(state, f)
state = load_state(state_file) if os.path.exists(state_file) else default_state


#Uncomment this when running via FastAPI
# if len(sys.argv) < 2:
#     raise ValueError("Please provide a file path to convert.")

# true_PCAP_path = sys.argv[1]

#Uncomment when running in VSCode
true_PCAP_path = "./TestPcap.pcapng"

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

print("true", true_PCAP_path)
print("CSV", PCAP_File.name)
base = os.path.splitext(PCAP_File.name)
print("base", base[0])
base_pcap = base[0]
print("base", base_pcap)

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

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{input}"),
    ]
)

qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )



prompt_structure = hub.pull("rlm/rag-prompt")







def rag_protocols():
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

def rag_pcap():
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

    print("PCAP ID", this_pcap_id)

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
    #vectorstore = FAISS.from_documents(doc_pcap_splits, embeddings)
    vectorstore = FAISS.load_local(folder_path="vectorstore_index.faiss", embeddings=embeddings, index_name=f"{index}", allow_dangerous_deserialization=True)

    retriever = vectorstore.as_retriever()

    #vectorstore.save_local(folder_path="vectorstore_index.faiss", index_name=f"{index}")

    #retriever will include the vectorstore and also chat history
    history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_q_prompt)

    qa_chain = create_stuff_documents_chain(llm, qa_prompt)
    rag_chain = create_retrieval_chain(history_aware_retriever, qa_chain)

    #Now we need object to store chat history and updates chat history for the chain

    def get_session_history(session_id: int) -> ChatMessageHistory:
        if session_id not in init_qa_store:
            init_qa_store[session_id] = ChatMessageHistory()
        return init_qa_store[session_id]


    history_aware_rag_chain = RunnableWithMessageHistory(
        rag_chain,
        lambda session_id: get_session_history(session_id),
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )

    # questions = ["What are all the protocols that you see in the trace?",
    #              "For each protocol what IP addresses are communicating with each other?",
    #              "What did I just ask?",
    #              "For the TCP protocol please list the pairs of ip addresses communicating with each other",
    #              "For TCP protocol, all packets with the same tuple comprised of source ip, source port, destination ip, destination port, belong to the same session.  Please list all sessions that are active in this trace.",
    #              "Study one of these sessions and draw a picture that represents the communication using mermaid format",
    #              ]
    questions = ["What are all the protocols that you see in the trace?"]

    print("PRELIM QA STORE: ", init_qa_store)

    for query in questions:
        relevant_pcap_docs = retriever.invoke(query)

        def format_docs(relevant_docs):
            return "\n\n".join(doc.page_content for doc in relevant_docs)

        generation = history_aware_rag_chain.invoke(
            {
            "input": query,
            "external_contexts": external_contexts,
            "messages": get_session_history(this_pcap_id)
            },
            config={"configurable": {"session_id": this_pcap_id}}
        )

        #print(generation)

        init_qa_store[this_pcap_id].add_messages(generation)


    print("NOW QA STORE: ", init_qa_store)

    connection = create_connection()

    if connection:
        update_query = """
        UPDATE pcaps
        SET ragged_yet = %s,
        SET vectorstore_path = %s,
        SET init_qa = %s,
        WHERE pcap_id = %s;
        """

        serialized_init_qa_store = convert_to_json(init_qa_store)
        init_qa_store_json = json.dumps(serialized_init_qa_store)
        execute_query(update_query, (True, index, init_qa_store_json, this_pcap_id))

        connection.close()
    

def answer_question(question):
    chat_store = {}

    connection = create_connection()
    if connection:
        select_query = "SELECT chat_history WHERE PCAP_FILEPATH=%s"
        result = fetch_query(connection, select_query, (true_PCAP_path,))
        if (result == []):
            chat_store = {}
        else: 
            chat_store = result
            
        connection.close()
    
    PCAP_File_Path = state['converted_pcap'] #PCAP that has been converted to CSV

    while os.path.getsize(PCAP_File_Path) == 0:
        time.sleep(0.1)

    #load in saved data that corresponds to the last_ragged_pcap

    
    vectorstore = FAISS.load_local(folder_path="vectorstore_index.faiss", embeddings=embeddings, index_name=f"{base_pcap}", allow_dangerous_deserialization=True)
    retriever = vectorstore.as_retriever()
    history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_q_prompt)

    qa_chain = create_stuff_documents_chain(llm, qa_prompt)
    rag_chain = create_retrieval_chain(history_aware_retriever, qa_chain)

    #Now we need object to store chat history and updates chat history for the chain
    def get_session_history(session_id: str) -> BaseChatMessageHistory:
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
        {"input": question},
        config={
            "configurable":{"session_id": "abc123"}
        }, #constructs a session_id key to put in the store
    )
    print(generation["answer"])



if (state['ragged_proto'] == False):
    connection = create_connection()

    if connection:
        create_table_query = '''
        CREATE TABLE IF NOT EXISTS protocols (
            proto_id SERIAL PRIMARY KEY,
            proto_filepath TEXT
        );  
        '''
        execute_query(connection, create_table_query)

        connection.close()
    rag_protocols()


connection = create_connection()

if connection:
    select_query = "SELECT pcap_filepath FROM pcaps WHERE pcap_filepath=%s"
    result = fetch_query(connection, select_query, (true_PCAP_path,))

    connection.close()

    if (result == []):
        print("about to rag_pcap")
        rag_pcap() #if we haven't ragged the pcap that was loaded into the sys args, rag
    else:
        #question = sys.argv[2] #or whatever it is
        question = "Tell me about all the IP addresses in the packet trace"
        #answer_question(question) #if we have, just answer the question using our already saved data



save_state(state_file, state) #save state at the end of every run of this subprocess