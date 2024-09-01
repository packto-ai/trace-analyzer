import os
import subprocess
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn