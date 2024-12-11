import os, shutil
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import FastAPI, Form, Query, UploadFile, File, Request
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from rag_proto import rag_protocols
from answer_question import answer_question
from init_json import init_json, save_state, load_state
from db_config import create_connection, execute_query, fetch_query
from serialize import deserialize_json, format_conversation
from init_pcap import init_pcap
from config import rag_pcap
from config_graph import config_graph
from typing import List, Dict

state_file = 'src/app_state.json'
default_state = init_json()
state = load_state(state_file) if os.path.exists(state_file) else default_state

if (state['ragged_proto'] == False):
    rag_protocols()

connection = create_connection()
if connection:
    create_table_query = '''
    CREATE TABLE IF NOT EXISTS pcap_groups (
        group_id SERIAL PRIMARY KEY,
        group_name TEXT NOT NULL UNIQUE,
        group_path TEXT NOT NULL UNIQUE,
        subnet TEXT,
        chat_history JSONB,
        init_qa JSONB,
        graph_state JSONB
    );  
    '''
    execute_query(connection, create_table_query)

    connection.close()

connection = create_connection()
if connection:
    create_table_query = '''
    CREATE TABLE IF NOT EXISTS llms (
        llm_id SERIAL PRIMARY KEY,
        llm_name TEXT NOT NULL,
        llm_type TEXT NOT NULL,
        api_key TEXT,
        base_url TEXT
    );  
    '''
    execute_query(connection, create_table_query)

    connection.close()

connection = create_connection()
if connection:
    create_table_query = '''
    CREATE TABLE IF NOT EXISTS pcaps (
        pcap_id SERIAL PRIMARY KEY,
        pcap_filepath TEXT NOT NULL UNIQUE,
        txt_filepath TEXT,
        group_id INT REFERENCES pcap_groups(group_id)
    );
    '''
    execute_query(connection, create_table_query)

    connection.close()

connection = create_connection()
if connection:
    create_table_query = '''
    CREATE TABLE IF NOT EXISTS vectors (
        doc_id SERIAL PRIMARY KEY,
        doc_content TEXT,
        embedding VECTOR(3072),
        pcap_filepath TEXT REFERENCES pcaps(pcap_filepath),
        pcap_id INT REFERENCES pcaps(pcap_id),
        group_id INT REFERENCES pcap_groups(group_id)
    );
    '''
    execute_query(connection, create_table_query)

    connection.close()
    
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

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://static-server:8009"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Mount the directory containing the html and js files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

#Home page which says Welcome and has buttons for choosing a file, uploading it, and then analyzing a file you've uploaded
@app.get("/", response_class=HTMLResponse)
async def welcome(request: Request):
    """
    This state is so that anytime we leave the chat_bot screen, the current session is cleared.
    We need this because we need a differentiator in the chat_bot screen between chat history and the current session
    But I don't want the current session to be in the database for permanent storage so store it in json for temporary storage
    But when we leave that chat_bot screen, we clear the current chat session and it has already been pushed to the database as part of 
    chat history. This way when we go back, the current session is blank but the chat history shows what was already a part of chat history
    and also the conversation from the previous session. In the database there is no difference, but for formatting to the user
    there is.
    """
    state.pop('initial_analysis', None)
    state.pop('chat_history', None)
    state.pop('session_chat', None)


    connection = create_connection()
    if connection:
        select_query = "SELECT group_id, group_name FROM pcap_groups;"
        groups = fetch_query(connection, select_query)


    groups_dict = []
    for group in groups:
        group_id = group[0]
        group_name = group[1]
        entry = {"group": group_name, "group_id": group_id}
        groups_dict.append(entry)

    print("GRAUPZ", groups_dict)
    
    return templates.TemplateResponse("index.html", {"request": request, "groups": groups_dict})

@app.post("/llm_setup")
async def llm_setup(    
    llm: str = Form(...),
    api_key: str = Form(None),
    base_url: str = Form(None)
    ):

    llm_type = ""
    if (api_key):
        llm_type = "Cloud"
    else:
        llm_type = "Local"

    connection = create_connection()
    if connection:
        insert_query = """
        INSERT INTO llms (llm_name, llm_type, api_key, base_url)
        VALUES (%s, %s, %s, %s)
        """
        execute_query(connection, insert_query, (llm, llm_type, api_key, base_url))

    global graph
    if llm_type == "Local":
        try:
            graph = config_graph(llm, base_url)
        except:
            return HTMLResponse(content="""
            <html>
            <body>
                <script>
                    alert("Error: Unable to implement LangGraph. Please try again.");
                    window.location.href = "/";
                </script>
            </body>
            </html>
        """, status_code=400)

    if llm_type == "Cloud":
        try:
            graph = config_graph(llm, api_key)
        except:
            return HTMLResponse(content="""
            <html>
            <body>
                <script>
                    alert("Error: Unable to implement LangGraph. Please try again.");
                    window.location.href = "/";
                </script>
            </body>
            </html>
        """, status_code=400)

    return RedirectResponse(url="/", status_code=303)


#Uploads the file by creating a directory in this project folder, which is basically acting as the server
#The directory created is called uploads and it puts any and all files that the user chooses as long as it's a pcap
@app.post("/upload")
async def upload_file(groupfolder: str = Form(...), 
                      files: list[UploadFile] = File(...)): #groupfolder is the name they put in textbox on home screen and files are the files they uploaded using the button
    
    print("groupfolder", groupfolder)

    upload_dir = "uploads"

    connection = create_connection()
    if connection:

        count_query = """
        SELECT COUNT(group_id)
        FROM pcap_groups;
        """
        output = fetch_query(connection, count_query)
        group_id = str(output[0][0] + 1)

        #if the groupname the user picked already exists, choose a different name
        os.makedirs(upload_dir, exist_ok=True)
        group_folder_path = f"{upload_dir}/{groupfolder}"
        try:
            os.makedirs(group_folder_path, exist_ok=False)
        except FileExistsError:
            return HTMLResponse(content="""
                <html>
                <body>
                    <script>
                        alert("Error: Group name already exists. Please choose a different name.");
                        window.location.href = "/";
                    </script>
                </body>
                </html>
            """, status_code=400)


        print("inserts", group_id, groupfolder, group_folder_path)

        insert_query = """
        INSERT INTO pcap_groups (group_id, group_name, group_path)
        VALUES (%s, %s, %s)
        """
        execute_query(connection, insert_query, (group_id, groupfolder, group_folder_path))

        print("GROUPZ", groupfolder)


        #for each file uploaded, basically add it to the group_folder
        for file in files:
            file_location = os.path.join(group_folder_path, file.filename)

            insert_query = """
            INSERT INTO pcaps (pcap_filepath, group_id)
            VALUES (%s, %s)
            """
            execute_query(connection, insert_query, (file_location, group_id))

            with open(file_location, "wb") as f:
                f.write(await file.read())

    
    state.pop('initial_analysis', None)
    state.pop('chat_history', None)
    state.pop('session_chat', None)

    return RedirectResponse(url="/", status_code=303)

@app.post("/add_pcaps")
async def add_pcaps(group_id: str = Form(...), files: list[UploadFile] = File(...)):

    upload_dir = "uploads"

    group_id = int(group_id)

    connection = create_connection()
    if connection:
        for file in files:
            filename = file.filename
            
            select_query = """
            SELECT group_name FROM pcap_groups WHERE group_id = %s;
            """
            output = fetch_query(connection, select_query, (group_id,))
            group_name = output[0][0]

            group_path = os.path.join(upload_dir, group_name)
            pcap_filepath = os.path.join(group_path, filename)

            with open(pcap_filepath, "wb") as f:
                f.write(await file.read())

            insert_query = """
            INSERT INTO pcaps (pcap_filepath, group_id)
            VALUES (%s, %s);
            """
            print("PCAP FILEPATH ADD", pcap_filepath)
            execute_query(connection, insert_query, (pcap_filepath, group_id))

    return RedirectResponse(url=f"/edit_group?group_id={group_id}", status_code=303)
    

#List all the groups that have been uploaded, and whichever one they click is sent as the "file" input to the run_analysis function below
@app.get("/add_group", response_class=HTMLResponse)
async def add_group(request: Request):
    # List all groups in the uploads directory which we created above
    state.pop('initial_analysis', None)
    state.pop('chat_history', None)
    state.pop('session_chat', None)

    return templates.TemplateResponse("add_group.html", {"request": request})

@app.get("/group_interface")
async def group_interface(request: Request, group: str, group_id: int):

    print("HFUASFHSU(FHS)")

    groupname = group.split('/', 1)[1]

    pcaps = [f"{filename}" for filename in os.listdir(group)]

    return templates.TemplateResponse("group_interface.html", {"request": request, "group": group, "group_id": group_id, "groupname": groupname, "pcaps": pcaps})

@app.get("/edit_group")
async def edit_group(request: Request, group_id: int):

    print("EDITS")
    
    connection = create_connection()
    if connection:
        select_query = """
        SELECT group_name, group_path 
        FROM pcap_groups 
        WHERE group_id = %s;
        """
        output = fetch_query(connection, select_query, (group_id,))
        group_name = output[0][0]
        group_path = output[0][1]

    pcaps = [f"{filename}" for filename in os.listdir(group_path)]

    print("GROUP NAME", group_name)
    print("GROUP PATH", group_path)
    print("GROUP PCAPS", pcaps)

    return templates.TemplateResponse("edit_group.html", {"request": request, "group_id": group_id, "group_path": group_path, "group_name": group_name, "pcaps": pcaps})


@app.delete("/delete_group")
async def delete_group(group_id: int):

    print("DELETE GROUP")

    connection = create_connection()
    if connection:

        select_query = "SELECT group_path FROM pcap_groups WHERE group_id = %s;"
        output = fetch_query(connection, select_query, (group_id,))
        print("OUTPUT DELETE GROUP", output)
        group_path = output[0][0]

        print("DELETE", group_path)
        shutil.rmtree(group_path)

        delete_query = "DELETE FROM pcaps WHERE group_id = %s"
        execute_query(connection, delete_query, (group_id,))

        delete_query = "DELETE FROM pcap_groups WHERE group_id=%s"
        execute_query(connection, delete_query, (group_id,))

    return RedirectResponse(url="/", status_code=303)

@app.delete("/delete_pcap")
async def delete_pcap(group_id: int, group_path: str, pcap: str):

    print("DELETE PCAP", group_id, group_path, pcap)

    pcap_filepath = os.path.join(group_path, pcap)
    print("FILEPATH", pcap_filepath)
    os.remove(pcap_filepath)

    connection = create_connection()
    if connection:
        delete_query = "DELETE FROM pcaps WHERE group_id=%s AND pcap_filepath=%s"
        execute_query(connection, delete_query, (group_id, pcap_filepath))

    return RedirectResponse(url=f"/edit_group?group_id={group_id}", status_code=303)


analysis_result = ""

@app.get("/run_analysis")
#runs the analysis on the file from the analysis function above
async def run_analysis(group_id: str):
    # Run packet_analyzer.py with the selected file
    #sends args to the the init_pcap.py function and then in packet_analyzer we access the file by using sys.argv[1] which refers to uploads/{file}
    print("HUH???")
    
    state.pop('initial_analysis', None)
    state.pop('chat_history', None)
    state.pop('session_chat', None)

    group_id = int(group_id)

    """
    We already know the path of the group folder and we want to send that entire path including the
    name of the file within it to init_pcap (we will also do this for init_pcap). I am trying to use absolute
    paths (relative to the project root) rather than have to constantly figure out relative paths
    So if the group path is uploads/group_name then this for loop will send uploads/group_name/pcap1 to init_pcap
    and uploads/group_name/pcap2 to init_pcap, and whatever else is in that group
    """

    connection = create_connection()
    if connection:
        select_query = "SELECT init_qa FROM pcap_groups WHERE group_id=%s"
        result = fetch_query(connection, select_query, (group_id,))

        select_query = "SELECT group_path from pcap_groups WHERE group_id=%s"
        group_result = fetch_query(connection, select_query, (group_id,))
        group = group_result[0][0]

        print("GROUP IS", group)

        files_in_group = [f"{group}/{filename}" for filename in os.listdir(group)]

        print("FILES IN GROUP IS", files_in_group)

        if result and result[0][0] is None:
            x = init_pcap(files_in_group, graph)
            if (x == "INVALID API KEY"):
                return HTMLResponse(content="""
                    <html>
                    <body>
                        <script>
                            alert("Error: INVALID API KEY.");
                            window.location.href = "/";
                        </script>
                    </body>
                    </html>
                """, status_code=400)

    #after init_pcap is done, go to the chat_bot with the current group as input
    print("ABOUT TO RETURN")
    return RedirectResponse(url=f"/chat_bot?group_id={group_id}", status_code=303)

#we have a get endpoint which shows all the previous interactions with packto
#and a post endpoint for asking new questions
@app.get("/chat_bot", response_class=HTMLResponse)
@app.post("/chat_bot", response_class=HTMLResponse)
async def chat_bot(request: Request, group_id: int, current_chat: Dict[str, List[Dict[str, str]]] = None, user_input: str = Form(None)): #user_input is only for the post endpoint. chat_bot calls itself in that case
    chat_history = None
    init_qa_store = None
    
    if current_chat == None:
        current_chat = {"chat": []}

    formatted_current_chat = ""
    group = ""

    if 'chat_history' not in state or 'initial_analysis' not in state:
        connection = create_connection()
        if connection:
            select_query = "SELECT chat_history, init_qa FROM pcap_groups WHERE group_id=%s"
            result = fetch_query(connection, select_query, (group_id,))
            if (result == []):
                chat_history = ""
            else: 
                chat_history = format_conversation(result[0][0]) if result[0][0] is not None else ""
                init_qa_store = format_conversation(result[0][1])
                chat_history = chat_history.replace("\n", "<br>")
                init_qa_store = init_qa_store.replace("\n", "<br>")
            connection.close()
        
        state['chat_history'] = chat_history
        state['initial_analysis'] = init_qa_store
        
    result = ""

    if request.method == "POST" and user_input:
        # Run answer_question with the user input and selected file
        """
        We already know the path of the group folder and we want to send that entire path including the
        name of the file within it to answer_question (we will also do this for init_pcap). I am trying to use absolute
        paths (relative to the project root) rather than have to constantly figure out relative paths
        So if the group path is uploads/group_name then this for loop will send uploads/group_name/pcap1 to answer_question
        and uploads/group_name/pcap2 to answer_question, and whatever else is in that group
        """

        print("POSTINGGGG")

        # #This is for when we have restarted chat_bot after closing it. we need the info necessary to create the graph to be in db and retrieve it
        connection = create_connection()
        print("CHECK 1")
        if connection:
            select_query = "SELECT group_path FROM pcap_groups WHERE group_id=%s"
            result = fetch_query(connection, select_query, (group_id,))
            print("CHECK 2")
            if result:
                print("resultsss", result)
                group = result[0][0]
            connection.close()
            print("CHECK 3")
        # graph = config_graph(llm_type, api_key)


        files_in_group = [f"{group}/{filename}" for filename in os.listdir(group)]
        result = answer_question(files_in_group, user_input, graph)

        if 'session_chat' not in state:
            state['session_chat'] = {"chat": []}
            

        current_chat = state['session_chat']
        current_chat["chat"].append({"sender": "Human", "message": user_input})
        current_chat["chat"].append({"sender": "Packto", "message": result})

        state['session_chat'] = current_chat
        # save_state(state_file, state)

        formatted_current_chat = format_conversation(current_chat)
        formatted_current_chat = formatted_current_chat.replace("\n", "<br>")


    # Display the chatbox UI with chat history and initial analysis and current session all separated
    return templates.TemplateResponse("chat.html", {"request": request, "group_id": group_id, "init_qa": state['initial_analysis'], "chat_history": state['chat_history'], "current_chat": formatted_current_chat})

if __name__ == "__main__":
    # Start the server
    uvicorn.run(app, host="0.0.0.0", port=8010)
