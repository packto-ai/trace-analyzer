# packto.ai

Instructions:
Make an account for docker and download docker desktop and wireshark
Docker Desktop: https://www.docker.com/products/docker-desktop/
Wireshark: https://www.wireshark.org/download.html

Go to your terminal (cmd, powershell, or VSCode, bash, whatever you prefer), use cd to go to whatever directory you want this project to live and type this command:
git clone git@github.com:TAJ-32/packto.ai.git

This should create a folder called packto.ai on your computer. Open it up by typing cd packto.ai.

Type ls. It should show all the files from the project directory on github. If it does, do the following:

Open Docker Desktop (sometimes this can be slow so restart your computer if it isn't working)
in the terminal where you have packto.ai open, type:
docker-compose down -v
Then type:
docker-compose up --build

Open up the app in your web browser at localhost:8009
