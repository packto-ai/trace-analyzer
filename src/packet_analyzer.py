import os
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
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from scraper import download_protocols
import sys
from convert import convert
from text_cutter import documentation_iteration


#Uncomment this when running via FastAPI
# if len(sys.argv) < 2:
#     raise ValueError("Please provide a file path to convert.")

# file_path = sys.argv[1]
# print(sys.argv)

# print("File path", file_path)


#Uncomment when running in VSCode
file_path = "./TestPcap.pcapng"



if not os.path.exists("./NetworkProtocols"):
    download_protocols()



#environment variables
load_dotenv(dotenv_path="C:/Users/sarta/OneDrive/Desktop/Coding_Stuff/LangChainPingInterpreter/keys.env")
openai_key = os.getenv('OPENAI_API_KEY')
langchain_key = os.getenv('LANGCHAIN_API_KEY')
mistral_key = os.getenv('MISTRAL_API_KEY')
gemini_key = os.getenv('GOOGLE_API_KEY')

if gemini_key is None:
    raise ValueError("Did not find MISTRAL_API_KEY. Please ensure it is set in your environment variables or .env file.")

llm = ChatMistralAI(model="mistral-large-latest", temperature=0)



#Convert pcap to CSV
PCAP_File = convert(file_path)






#######
#The following is RAG on Protocol Documentation
#######
#Docs to index for our initial RAG. These will augment the knowledge of our 
#LLM to know more about Network Protocols
Protocol_File_Paths = []

#split the documents through text_cutter.py
documentation_iteration()

directory = 'SplitDocumentation'
for filename in os.listdir(directory):
    Protocol_File_Paths.append(os.path.join(directory, filename))

# for path in Protocol_File_Paths:
#     print(path)



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
# vectorstore = FAISS.from_documents(doc_proto_splits, embeddings)
# retriever = vectorstore.as_retriever()

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

#retriever will include the vectorstore and also chat history
# history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_q_prompt)

#build functionality for chat history
system_prompt = (
    "You are an expert on Network Protocols and answering questions about packet traces. "
    "Use the following pieces of retrieved context to answer "
    "the question. If you don't know the answer, say that you "
    "don't know."
    "\n\n"
    "{context}"
)
qa_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

qa_chain = create_stuff_documents_chain(llm, qa_prompt)
# rag_chain = create_retrieval_chain(history_aware_retriever, qa_chain)

#Now we need object to store chat history and updates chat history for the chain
store = {} #will store chat history

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

# history_aware_rag_chain = RunnableWithMessageHistory(
#     rag_chain,
#     get_session_history,
#     input_messages_key="input",
#     history_messages_key="chat_history",
#     output_messages_key="answer",
# )

prompt_structure = hub.pull("rlm/rag-prompt")

question = "Tell me about all the Network Protocols"
# relevant_proto_docs = retriever.invoke(question)

def format_docs(relevant_proto_docs):
    return "\n\n".join(doc.page_content for doc in relevant_proto_docs)

# generation = history_aware_rag_chain.invoke(
#     {"input": question},
#     config={
#         "configurable":{"session_id": "abc123"}
#     }, #constructs a session_id key to put in the store
# )
# print(generation["answer"])

# generation = history_aware_rag_chain.invoke(
#     {"input": "what was the first question I asked?"},
#     config={
#         "configurable":{"session_id": "abc123"}
#     }, #constructs a session_id key to put in the store
# )
# print(generation["answer"])






#######
#The following is RAG on sample pcap
#######
#Docs to index for our initial RAG. These will augment the knowledge of our 
#LLM to know more about pcaps
PCAP_File_Path = PCAP_File.name

# if (os.path.exists("TestTrace.csv")):
#     print("YEAH IT EXISTS")

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

#create vectorstore
vectorstore = FAISS.from_documents(doc_pcap_splits, embeddings)
retriever = vectorstore.as_retriever()

contextualize_q_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

#retriever will include the vectorstore and also chat history
history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_q_prompt)

qa_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

qa_chain = create_stuff_documents_chain(llm, qa_prompt)
rag_chain = create_retrieval_chain(history_aware_retriever, qa_chain)

#Now we need object to store chat history and updates chat history for the chain

history_aware_rag_chain = RunnableWithMessageHistory(
    rag_chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
    output_messages_key="answer",
)

prompt_structure = hub.pull("rlm/rag-prompt")

# questions = ["What are all the protocols that you see in the trace?",
#              "For each protocol what IP addresses are communicating with each other?",
#              "What did I just ask?",
#              "For the TCP protocol please list the pairs of ip addresses communicating with each other",
#              "For TCP protocol, all packets with the same tuple comprised of source ip, source port, destination ip, destination port, belong to the same session.  Please list all sessions that are active in this trace.",
#              "Study one of these sessions and draw a picture that represents the communication using mermaid format",
#              ]
questions = ["What are all the protocols that you see in the trace?"]

for query in questions:
    relevant_pcap_docs = retriever.invoke(query)

    def format_docs(relevant_docs):
        return "\n\n".join(doc.page_content for doc in relevant_docs)

    rag_chain = prompt_structure | llm | StrOutputParser()

    generation = history_aware_rag_chain.invoke(
        {"input": query},
        config={
            "configurable":{"session_id": "abc123"}
        }, #constructs a session_id key to put in the store
    )
    print(generation["answer"])