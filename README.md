﻿# packto.ai

Instructions:
Make an account for docker and download docker desktop
Docker Desktop: https://www.docker.com/products/docker-desktop/

Go to your terminal (cmd, powershell, or VSCode, bash, whatever you prefer), use **cd** to go to whatever directory you want this app to live and type this command:
**git clone https://github.com/packto-ai/trace-analyzer.git**

This should create a folder called trace-analyzer on your computer. Open it up by typing **cd trace-analyzer**

Type **ls**. It should show all the files from the project directory on github. If it does, do the following:

Open Docker Desktop
In the terminal where yo have the trace-analyzer open, type:
**docker-compose down -v**
Then type:
**docker-compose up --build**

Open up the app in your web browser at **localhost:8009**
