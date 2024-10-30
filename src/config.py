import sys
import os

#FUNCTION TO create a group of PCAPs in the database after user uploads one. Essentially initializes stuff for the db so analysis
#can be done on a group of PCAPs. Also vectorizes them so that we can do RAG
def rag_pcap(PCAPS, group_id):
    import time
    from langchain_mistralai import ChatMistralAI
    from langchain import hub
    from langchain_community.document_loaders import TextLoader
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
    from convert import convert
    from db_config import create_connection, execute_query
    from init_json import init_json, load_state

    state_file = 'src/app_state.json'
    default_state = init_json()
    state = load_state(state_file) if os.path.exists(state_file) else default_state

    #Make protocol folder for network protocols to scrape and then actually gather them
    if not os.path.exists("./NetworkProtocols"):
        download_protocols()

    #environment variables
    load_dotenv(dotenv_path="C:/Users/sarta/BigProjects/packto.ai/keys.env")
    mistral_key = os.getenv('MISTRAL_API_KEY')

    if mistral_key is None:
        raise ValueError("Did not find MISTRAL_API_KEY. Please ensure it is set in your environment variables or .env file.")

    llm = ChatMistralAI(model="mistral-large-latest", temperature=0)

    #convert each PCAP to a text file using scapy so it can be RAGed on
    for true_PCAP_path in PCAPS:
        txt_file = convert(true_PCAP_path)
        base = os.path.splitext(txt_file.name)
        base_pcap = base[0]

        #the following variables are constant across everything these don't ever need to change
        embeddings = OpenAIEmbeddings(model="text-embedding-3-large") #3072 dimensions #GoogleGenerativeAIEmbeddings(model="models/embedding-001")

        #######
        #The following is RAG on sample pcap
        #######
        #Docs to index for our initial RAG. These will augment the knowledge of our 
        #LLM to know more about pcaps
        
        #Create PCAP TABLE
        connection = create_connection()
        this_pcap_id = 0
        if connection:
            insert_sql_query = """
            INSERT INTO pcaps (pcap_filepath, txt_filepath, group_id) 
            VALUES (%s, %s, %s)
            RETURNING pcap_id;
            """
            this_pcap_id = execute_query(connection, insert_sql_query, (true_PCAP_path, txt_file.name, group_id))

            connection.close()

        while os.path.getsize(txt_file.name) == 0:
            time.sleep(0.1)


        #THE REST OF THIS IS ACTUALLY VECTORIZING AND THEN STORING THE VECTORS IN THE DB. IT TAKES A RIDICULOUSLY LONG TIME SO I AM
        #COMMENTING IT OUT FOR NOW

        # loader = TextLoader(file_path=txt_file.name)  #we might have to make our own file loader for pcap files

        # docs_pcap = loader.load()

        # if not docs_pcap:
        #     raise ValueError("No documents were loaded. Please check the CSV file.")

        # def clean_metadata(doc):
        #     for key, value in doc.metadata.items():
        #         if isinstance(value, list):
        #             # Convert list to a comma-separated string or handle it as needed
        #             doc.metadata[key] = ', '.join(value)
        #         # Add other necessary conversions if needed
        #     return doc

        # # Apply the cleaning function to all documents
        # cleaned_documents = [clean_metadata(doc) for doc in docs_pcap]

        # #split them line by line, as they are formatted in tcpdump so that each
        # #document is a new packet essentially
        # text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(separators=["\n", ",", " "], chunk_size=500, chunk_overlap=200)
        # doc_pcap_splits = text_splitter.split_documents(cleaned_documents)

        # index = base_pcap
        # #create vectorstore
        # vectorstore = FAISS.from_documents(doc_pcap_splits, embeddings)

        # num_vectors = vectorstore.index.ntotal
        # doc_embeddings = vectorstore.index.reconstruct_n(0, num_vectors)
        # doc_texts = [doc.page_content for doc in vectorstore.docstore._dict.values()]

        # connection = create_connection()

        # if connection:
        #     for content, embedding in zip(doc_texts, doc_embeddings):
        #         embedding_list = embedding.tolist()
        #         insert_sql_query = """
        #         INSERT INTO vectors (doc_content, embedding, pcap_filepath, pcap_id, group_id)
        #         VALUES (%s, %s, %s, %s, %s);
        #         """
        #         execute_query(connection, insert_sql_query, (content, embedding_list, true_PCAP_path, this_pcap_id, group_id))

        #     connection.close()