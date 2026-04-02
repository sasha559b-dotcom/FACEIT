from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from auth_utils import verify_telegram_init_data, get_current_user

router = APIRouter()

def get_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=RealDictCursor)

class RegisterRequest(BaseModel):
    username: str
    game_id: str
    init_data: str

class LoginRequest(BaseModel):
    init_data: str

@router.post("/register")
def register(req: RegisterRequest):
    try:
        tg_user = verify_telegram_init_data(req.init_data)
        telegram_id = str(tg_user.get("id", ""))
    except:
        telegram_id = req.init_data if req.init_data.isdigit() else str(hash(req.init_data))[:10]

    if not telegram_id:
        raise HTTPException(400, "Invalid auth data")

    username = req.username.strip()
    game_id = req.game_id.strip()

    if len(username) < 3 or len(username) > 20:
        raise HTTPException(400, "Username must be 3-20 characters")
    if not username.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(400, "Username can only contain letters, numbers, _ and -")
    if not game_id:
        raise HTTPException(400, "Game ID is required")

    conn = get_conn(); cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE telegram_id = %s", (telegram_id,))
    if cur.fetchone():
        conn.close(); raise HTTPException(400, "Already registered")

    cur.execute("SELECT id FROM users WHERE username = %s", (username,))
    if cur.fetchone():
        conn.close(); raise HTTPException(400, "Username already taken")

    cur.execute("SELECT COUNT(*) as cnt FROM users")
    count = cur.fetchone()["cnt"]
    role = "developer" if count == 0 else "player"
    colors = ["#6366f1", "#ec4899", "#f59e0b", "#10b981", "#3b82f6", "#ef4444", "#8b5cf6"]
    color = colors[count % len(colors)]

    cur.execute(
        "INSERT INTO users (telegram_id, username, game_id, role, avatar_color) VALUES (%s, %s, %s, %s, %s)",
        (telegram_id, username, game_id, role, color)
    )
    conn.commit()

    cur.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
    user = cur.fetchone(); conn.close()
    return {"success": True, "user": dict(user)}

@router.post("/login")
def login(req: LoginRequest):
    try:
        tg_user = verify_telegram_init_data(req.init_data)
        telegram_id = str(tg_user.get("id", ""))
    except:
        telegram_id = req.init_data if req.init_data.isdigit() else str(hash(req.init_data))[:10]

    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
    user = cur.fetchone(); conn.close()

    if not user:
        return {"registered": False}
    return {"registered": True, "user": dict(user)}

@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return current_user
