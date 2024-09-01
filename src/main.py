import os
import subprocess
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn

app = FastAPI()

#Home page which says Welcome and has buttons for choosing a file, uploading it, and then analyzing a file you've uploaded
@app.get("/", response_class=HTMLResponse)
async def welcome():
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
    </body>
    </html>
    """

#Uploads the file by creating a directory in this project folder, which is basically acting as the server
#The directory created is called uploads and it puts any and all files that the user chooses as long as it's a pcap
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
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

@app.get("/run_analysis")
#runs the analysis on the file from the analysis function above
async def run_analysis(file: str):
    # Run packet_analyze.py with the selected file
    #sends args to the the packet_analyze.py function and then in packet_analyze we access the file by using sys.argv[1] which refers to uploads/{file}
    result = subprocess.run(["python", "src/packet_analyze.py", f"uploads/{file}"], capture_output=True, text=True)
    
    # Check if there was an error in running packet_analyze.py
    if result.returncode != 0:
        return HTMLResponse(content=f"<pre>Error: {result.stderr}</pre>", status_code=500)
    
    return HTMLResponse(content=f"<pre>{result.stdout}</pre>", status_code=200)

if __name__ == "__main__":
    # Start the server
    uvicorn.run(app, host="127.0.0.1", port=8000)
