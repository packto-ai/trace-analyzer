import os
import subprocess
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
from rag_proto import rag_protocols
from rag_pcap import rag_pcap
from answer_question import answer_question
from init_json import init_json, save_state, load_state
from db_config import create_connection, execute_query, fetch_query
from serialize import deserialize_json, format_conversation

state_file = 'src/app_state.json'
default_state = init_json()
state = load_state(state_file) if os.path.exists(state_file) else default_state

if (state['ragged_proto'] == False):
    rag_protocols()

app = FastAPI()

#Home page which says Welcome and has buttons for choosing a file, uploading it, and then analyzing a file you've uploaded
@app.get("/", response_class=HTMLResponse)
async def welcome():
    state.pop('initial_analysis', None)
    state.pop('chat', None)
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
            <input type="file" name="file">
            <button type="submit">Upload</button>
        </form>
        <form action="/analyze" method="get">
            <button type="submit">Analyze</button>
        </form>
        <form action="/user_pcaps" method="get">
            <button type="submit">My PCAPS</button>
        </form>
    </body>
    </html>
    """

#Uploads the file by creating a directory in this project folder, which is basically acting as the server
#The directory created is called uploads and it puts any and all files that the user chooses as long as it's a pcap
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    state.pop('initial_analysis', None)
    state.pop('chat_history', None)
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_location = f"{upload_dir}/{file.filename}"
    with open(file_location, "wb") as f:
        f.write(await file.read())
    return RedirectResponse(url="/", status_code=303)


#List all the files that have been uploaded, and whichever one they click is sent as the "file" input to the run_analysis function below
@app.get("/analyze", response_class=HTMLResponse)
async def analyze():
    # List all files in the uploads directory which we created above
    state.pop('initial_analysis', None)
    state.pop('chat', None)
    files = os.listdir("uploads")
    file_links = "".join(f'<li><a href="/run_analysis?file={file}">{file}</a></li>' for file in files)
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

#List all the files that have been uploaded, and whichever one they click is sent as the "file" input to the run_analysis function below
@app.get("/user_pcaps", response_class=HTMLResponse)
async def user_pcaps():
    state.pop('initial_analysis', None)
    state.pop('chat', None)
    # List all files in the uploads directory which we created above
    files = os.listdir("user_pcaps")
    file_links = "".join(f'<li><a href="/chat_bot?file={file}">{file}</a></li>' for file in files)
    return f"""
    <html>
    <body>
        <h2>Ask packto about any of these files:</h2>
        <ul>
            {file_links}
        </ul>
    </body>
    </html>
    """

analysis_result = ""

@app.get("/run_analysis")
#runs the analysis on the file from the analysis function above
async def run_analysis(file: str):
    # Run packet_analyzer.py with the selected file
    #sends args to the the packet_analyzer.py function and then in packet_analyzer we access the file by using sys.argv[1] which refers to uploads/{file}
    state.pop('initial_analysis', None)
    state.pop('chat', None)
    rag_pcap(file)

    return RedirectResponse(url=f"/chat_bot?file={file}", status_code=303)




@app.get("/chat_bot", response_class=HTMLResponse)
@app.post("/chat_bot", response_class=HTMLResponse)
async def chat_bot(request: Request, file: str, user_input: str = Form(None)):
    chat_history = None
    init_qa_store = None
    
    if 'initial_analysis' not in state or 'chat_history' not in state:
        connection = create_connection()
        if connection:
            select_query = "SELECT chat_history, init_qa FROM pcaps WHERE pcap_filepath=%s"
            result = fetch_query(connection, select_query, (file,))
            if (result == []):
                chat_history = {}
            else: 
                chat_history = format_conversation(result[0][0]) if result[0][0] is not None else {}
                init_qa_store = format_conversation(result[0][1])
            connection.close()
        
        state['initial_analysis'] = f"<div class='message bot'>Initial Analysis:<pre>{init_qa_store}</pre></div>"
        state['chat_history'] = f"<div class='message bot'>Previous Chat History:<pre>{chat_history}</pre></div>"

    result = ""
    if request.method == "POST" and user_input:
        # Run answer_question with the user input and selected file
        result = answer_question(file, user_input)
        # if result.returncode != 0:
        #     analysis_result = f"Error: {result.stderr}"
        # else:
        #     analysis_result = result.stdout
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
            <div class="message bot"><pre>{result}</pre></div>
            <div class="message user"><pre>{user_input}</pre></div>
            <div class="message bot">Current Chat:</div>
            {state['chat_history']}
            {state['initial_analysis']}
        </div>
        <form action="/chat_bot?file={file}" method="post" style="position: fixed; bottom: 0; width: 100%; background: #fff; padding: 10px; box-shadow: 0 -1px 5px rgba(0,0,0,0.1);">
            <input type="text" name="user_input" placeholder="Type your message here..." style="width: 80%; padding: 10px; border: 1px solid #ccc; border-radius: 4px;" value="">
            <button type="submit" style="padding: 10px 20px; border: none; background-color: #007BFF; color: white; border-radius: 4px; cursor: pointer;">Send</button>
        </form>
    </body>
    </html>
    """

if __name__ == "__main__":
    # Start the server
    uvicorn.run(app, host="127.0.0.1", port=8000)
