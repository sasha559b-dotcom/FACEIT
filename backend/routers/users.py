from fastapi import APIRouter, HTTPException, Depends, Query
import sqlite3
from database import DB_PATH
from auth_utils import get_current_user

router = APIRouter()

def row_to_dict(row):
    return dict(row) if row else None

def elo_to_rank(elo: int) -> dict:
    if elo < 800:
        return {"name": "Iron", "color": "#6b7280", "icon": "🪨"}
    elif elo < 1000:
        return {"name": "Bronze", "color": "#92400e", "icon": "🥉"}
    elif elo < 1200:
        return {"name": "Silver", "color": "#9ca3af", "icon": "🥈"}
    elif elo < 1500:
        return {"name": "Gold", "color": "#f59e0b", "icon": "🥇"}
    elif elo < 1800:
        return {"name": "Platinum", "color": "#6366f1", "icon": "💎"}
    elif elo < 2100:
        return {"name": "Diamond", "color": "#06b6d4", "icon": "💠"}
    elif elo < 2500:
        return {"name": "Master", "color": "#8b5cf6", "icon": "👑"}
    else:
        return {"name": "Grandmaster", "color": "#ef4444", "icon": "🔥"}

@router.get("/leaderboard")
def leaderboard(limit: int = Query(50, le=100)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    users = conn.execute(
        """SELECT id, username, game_id, elo, wins, losses, role, avatar_color
           FROM users WHERE is_banned = 0
           ORDER BY elo DESC LIMIT ?""", (limit,)
    ).fetchall()
    conn.close()
    result = []
    for i, u in enumerate(users):
        d = dict(u)
        d["rank"] = i + 1
        d["rank_info"] = elo_to_rank(d["elo"])
        total = d["wins"] + d["losses"]
        d["winrate"] = round(d["wins"] / total * 100) if total > 0 else 0
        result.append(d)
    return result

@router.get("/{user_id}")
def get_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if not user:
        raise HTTPException(404, "User not found")
    d = dict(user)
    d["rank_info"] = elo_to_rank(d["elo"])
    total = d["wins"] + d["losses"]
    d["winrate"] = round(d["wins"] / total * 100) if total > 0 else 0
    return d

@router.get("/")
def get_users(search: str = Query(None)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if search:
        users = conn.execute(
            "SELECT * FROM users WHERE username LIKE ? OR game_id LIKE ? LIMIT 20",
            (f"%{search}%", f"%{search}%")
        ).fetchall()
    else:
        users = conn.execute("SELECT * FROM users ORDER BY elo DESC LIMIT 50").fetchall()
    conn.close()
    result = []
    for u in users:
        d = dict(u)
        d["rank_info"] = elo_to_rank(d["elo"])
        result.append(d)
    return result
