# packto.ai's TraceAnalyzer
 
## Configuration
1. Make an account for docker and download docker desktop
Docker Desktop: https://www.docker.com/products/docker-desktop/

2. Go to your terminal (cmd, powershell, or VSCode, bash, whatever you prefer), use **cd** to go to whatever directory you want this app to live and type this command:
**git clone https://github.com/packto-ai/trace-analyzer.git**

3. This should create a folder called trace-analyzer on your computer. Open it up by typing **cd trace-analyzer**

4. Type **ls**. It should show all the files from the project directory on github. If it does, do the following:

5. Open Docker Desktop

7. In the terminal where yo have the trace-analyzer open, type:
**docker-compose down -v**
Then type:
**docker-compose up --build**

8. Open up the app in your web browser at **localhost:8009**

## Purpose:
Packto’s TraceAnalyzer tool is our open-source Agentic AI System for contextual packet trace analysis. Just as other tools like Wireshark and tcpdump can be used for filtering, visualizing, and following streams of network data, TraceAnalyzer implements that same functionality but with NLP. Rather than navigating various tools, filter codes, and CLI commands, simply ask TraceAnalyzer questions about a packet trace and receive answers in natural language. 

TraceAnalyzer also allows for analysis of several traces concurrently (see **TraceGroups** in **Features**), opening endless possibilities for holistic packet trace analysis that other tools do not have. We invite you to use and contribute! 

## How To Use:
After you have TraceAnalyzer open in your web browser, select an LLM. Either use an API key to use a cloud version of OpenAI, Anthropic, and Mistral or use a local model with LMStudio (See their docs for reference on how to host an LLM locally) and use the base URL for the LLM you are hosting.

Now, simply add a **TraceGroup** in the left panel, name it, select the files you want (up to 50MB total) and click on the trace in the list of **TraceGroups** in the left panel. You will see some initial questions that TraceAnalyzer answers by default in the **Initial Analysis** section of the chat section of the page. The section is split between **Initial Analysis** for these default questions and answers, **Chat History** for conversations from a previous session (all of this is used as context for new questions you ask), and **Current Chat** to easily navigate your current conversation.

To deselect your current **TraceGroup**, click the logo in the top left corner and return to the default home page.

**TraceGroups** can also be edited to delete specific PCAPs or add new ones (as long as the total file size is still under 50MB), or you can delete the entire group by clicking the three dots next to the **TraceGroup’s** name. 

## Features
### TraceGroups
One of the groundbreaking parts of TraceAnalyzer is its ability to analyze several traces at once. This is possible because the system is composed of a collection of tools that are implemented using **LangChain**. (Show Picture of the tcp_session tool). These tools are Python functions that take an array of file names that the user uploaded to a **TraceGroup**. Wireshark’s python library **pyshark** is used to analyze them one at a time and the results are handed to the user-selected LLM as a group of strings (each string being the result of a single trace’s analysis) to be interpreted holistically. This, combined with our prompt engineering that specifies the LLM to interpret a group of files instead of one, allows TraceAnalyzer to process the results from several traces in Natural Language while still differentiating between them as individual files.
### LLM Agnostic
Through LangChain’s open source library, TraceAnalyzer can normalize LLM use so that users can pick any LLM that has API endpoints that are supported by **LangChain**, whether the model is hosted locally or on the cloud.
### Chain of Thought and RAG
TraceAnalyzer’s system builds off of its own output so that it actively builds off of the chat session a user is having with it to become more and more knowledgeable about the **TraceGroup** it’s working on. It takes chat history and previous tools as external knowledge to answer new questions so that every question can be answered contextually rather than as a standalone. 
In addition to contextualizing answers, TraceAnalyzer’s selected LLM uses RAG to vectorize Official Network Protocol documentation to augment its knowledge base. This allows the model to have easy access to a wealth of knowledge on network protocols, which increases information coverage and makes answers far more coherent.

## Architecture
TraceAnalzyer has three main components:
### Web Container
Using Docker’s nginx container, we set up a web server with slight modifications to allow 50MB of input. This allows the frontend experience to be hosted at localhost:8009 while our backend API operations are hosted separately via FastAPI at localhost: 8010
### API
This is what contains all of our AI Agent and System logic, including LLM Selection, RAG, Prompt Engineering, tool use, and more. All written in Python.
### Database Container
Using PostgreSQL’s Docker Container, all of the data on **TraceGroups**, chat history, and network protocol documentation vectors is easily accessible by the API so that the LLM can serve content dynamically and directly to the user via the nginx Web Server container.

## Third-Party Tools Used:
**LangChain (See LLM Agnostic in Features)**

**Docker (See Architecture)**

**FastAPI (See Architecture)**

**PostgreSQL (See Architecture)**

**Pyshark (See TraceGroups in Features)**
