import os
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
from rag_proto import rag_protocols
from answer_question import answer_question
from init_json import init_json, save_state, load_state
from db_config import create_connection, execute_query, fetch_query
from serialize import deserialize_json, format_conversation
from init_pcap import init_pcap
from config import rag_pcap

state_file = 'src/app_state.json'
default_state = init_json()
state = load_state(state_file) if os.path.exists(state_file) else default_state

if (state['ragged_proto'] == False):
    rag_protocols()

print("GOING TO")
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

#Home page which says Welcome and has buttons for choosing a file, uploading it, and then analyzing a file you've uploaded
@app.get("/", response_class=HTMLResponse)
async def welcome():
    state.pop('initial_analysis', None)
    state.pop('chat_history', None)
    state.pop('session_chat', None)
    
    return """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>packto.ai</title>
    </head>
    <body>
        <h1>Welcome!</h1>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="text" name="groupfolder" placeholder="Enter group name" required>
            <input type="file" name="files" multiple>
            <button type="submit">Upload</button>
        </form>
        <form action="/analyze" method="get">
            <button type="submit">My PCAPS</button>
        </form>
    </body>
    </html>
    """

#Uploads the file by creating a directory in this project folder, which is basically acting as the server
#The directory created is called uploads and it puts any and all files that the user chooses as long as it's a pcap
@app.post("/upload")
async def upload_file(groupfolder: str = Form(...), files: list[UploadFile] = File(...)):
    state.pop('initial_analysis', None)
    state.pop('chat_history', None)
    state.pop('session_chat', None)
    upload_dir = "uploads"

    connection = create_connection()
    if connection:
        count_query = """
        SELECT COUNT(group_id)
        FROM pcap_groups;
        """
        output = fetch_query(connection, count_query)
        group_id = str(output[0][0] + 1)

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
    
    connection = create_connection()
    if connection:
        insert_query = """
        INSERT INTO pcap_groups (group_id, group_name, group_path)
        VALUES (%s, %s, %s);
        """
        execute_query(connection, insert_query, (group_id, groupfolder, group_folder_path))

    for file in files:
        file_location = os.path.join(group_folder_path, file.filename)

        with open(file_location, "wb") as f:
            f.write(await file.read())

    files_in_group = [f"uploads/{groupfolder}/{filename}" for filename in os.listdir(group_folder_path)]
    rag_pcap(files_in_group, group_id)

    return RedirectResponse(url="/", status_code=303)


#List all the groups that have been uploaded, and whichever one they click is sent as the "file" input to the run_analysis function below
@app.get("/analyze", response_class=HTMLResponse)
async def analyze():
    # List all groups in the uploads directory which we created above
    state.pop('initial_analysis', None)
    state.pop('chat_history', None)
    state.pop('session_chat', None)
    groups = os.listdir("uploads")
    file_links = ""

    for group in groups:
        print("GROUP", type(group))

        connection = create_connection()
        if connection:
            count_query = """
            SELECT group_id
            FROM pcap_groups
            WHERE group_name = %s;
            """
            output = fetch_query(connection, count_query, (group,))

            if output:
                group_id = output[0][0]

                print(group_id)

                connection = create_connection()
                if connection:
                    select_query = "SELECT init_qa FROM pcap_groups WHERE group_id=%s"
                    result = fetch_query(connection, select_query, (group_id,))
                    if result[0][0] != None:
                        file_links += f'<li><a href="/chat_bot?group=uploads/{group}">{group}</a></li>'
                    else:
                        file_links += f'<li><a href="/run_analysis?group=uploads/{group}">{group}</a></li>'

                    connection.close()
            
    return f"""
    <html>
    <body>
        <h2>Select a file to analyze:</h2>
        <ul>
            {file_links}
        </ul>
    </body>
    </html>
    """

analysis_result = ""

@app.get("/run_analysis")
#runs the analysis on the file from the analysis function above
async def run_analysis(group: str):
    # Run packet_analyzer.py with the selected file
    #sends args to the the init_pcap.py function and then in packet_analyzer we access the file by using sys.argv[1] which refers to uploads/{file}
    state.pop('initial_analysis', None)
    state.pop('chat_history', None)
    state.pop('session_chat', None)

    print("FILE", group)

    files_in_group = [f"{group}/{filename}" for filename in os.listdir(group)]
    print("Files", files_in_group)

    init_pcap(files_in_group)

    return RedirectResponse(url=f"/chat_bot?group={group}", status_code=303)




@app.get("/chat_bot", response_class=HTMLResponse)
@app.post("/chat_bot", response_class=HTMLResponse)
async def chat_bot(request: Request, group: str, user_input: str = Form(None)):
    chat_history = None
    init_qa_store = None
    
    if 'initial_analysis' not in state or 'chat_history' not in state:
        connection = create_connection()
        if connection:
            select_query = "SELECT chat_history, init_qa FROM pcap_groups WHERE group_path=%s"
            result = fetch_query(connection, select_query, (group,))
            if (result == []):
                chat_history = {}
            else: 
                chat_history = format_conversation(result[0][0]) if result[0][0] is not None else {}
                init_qa_store = format_conversation(result[0][1])
            connection.close()
        
        state['initial_analysis'] = f"<div class='message bot'>Initial Analysis:<pre>{init_qa_store}</pre></div>"
        state['chat_history'] = f"<div class='message bot'>Previous Chat History:<pre>{chat_history}</pre></div>"

    result = ""
    if 'session_chat' not in state:
        state['session_chat'] = ""
    if request.method == "POST" and user_input:
        # Run answer_question with the user input and selected file
        files_in_group = [f"{group}/{filename}" for filename in os.listdir(group)]
        result = answer_question(files_in_group, user_input)
        state['session_chat'] = f"<div class='message user'><pre>You: {user_input}\n</pre></div>" + state['session_chat']
        state['session_chat'] = f"<div class='message bot'><pre>AI: {result}\n</pre></div>" + state['session_chat']

    # Display the chatbox UI with chat history
    return f"""
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Chat Bot</title>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            #chat-box {{ border:1px solid #ccc; padding:10px; height:300px; overflow-y:scroll; display:flex; flex-direction:column-reverse; }}
            .message {{ margin-bottom: 10px; }}
            .user {{ font-weight: bold; }}
            .bot {{ color: blue; }}
        </style>
    </head>
    <body>
        <h2>PACKTO</h2>
        <div id="chat-box">
            {state['session_chat']}
            <div class="message bot">Current Chat:</div>
            {state['chat_history']}
            {state['initial_analysis']}
        </div>
        <form action="/chat_bot?group={group}" method="post" style="position: fixed; bottom: 0; width: 100%; background: #fff; padding: 10px; box-shadow: 0 -1px 5px rgba(0,0,0,0.1);">
            <input type="text" name="user_input" placeholder="Type your message here..." style="width: 80%; padding: 10px; border: 1px solid #ccc; border-radius: 4px;" value="">
            <button type="submit" style="padding: 10px 20px; border: none; background-color: #007BFF; color: white; border-radius: 4px; cursor: pointer;">Send</button>
        </form>
    </body>
    </html>
    """

if __name__ == "__main__":
    # Start the server
    uvicorn.run(app, host="0.0.0.0", port=8010)
