from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import sqlite3
from database import DB_PATH
from auth_utils import get_current_user, require_role

router = APIRouter()

class BanRequest(BaseModel):
    user_id: int
    reason: str = "No reason given"

class MuteRequest(BaseModel):
    user_id: int
    reason: str = "No reason given"

class EloRequest(BaseModel):
    user_id: int
    elo: int
    reason: str = ""

class RoleRequest(BaseModel):
    user_id: int
    role: str  # player, moderator, admin, developer

class MapRequest(BaseModel):
    name: str
    image_url: str = ""

ROLE_HIERARCHY = {"player": 0, "moderator": 1, "admin": 2, "developer": 3}

def log_action(conn, admin_id, action, target_id, details=""):
    conn.execute(
        "INSERT INTO audit_log (admin_id, action, target_user_id, details) VALUES (?, ?, ?, ?)",
        (admin_id, action, target_id, details)
    )

def check_can_target(actor: dict, target_role: str):
    actor_level = ROLE_HIERARCHY.get(actor["role"], 0)
    target_level = ROLE_HIERARCHY.get(target_role, 0)
    if actor_level <= target_level:
        raise HTTPException(403, "Cannot perform action on user with equal or higher role")

# --- MODERATOR ACTIONS ---

@router.post("/mute")
def mute_user(req: MuteRequest, current_user: dict = Depends(require_role("moderator"))):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    target = conn.execute("SELECT * FROM users WHERE id = ?", (req.user_id,)).fetchone()
    if not target:
        conn.close()
        raise HTTPException(404, "User not found")
    check_can_target(current_user, target["role"])
    conn.execute("UPDATE users SET is_muted = 1, mute_reason = ? WHERE id = ?", (req.reason, req.user_id))
    log_action(conn, current_user["id"], "mute", req.user_id, req.reason)
    conn.commit()
    conn.close()
    return {"success": True, "message": f"User muted: {req.reason}"}

@router.post("/unmute")
def unmute_user(req: MuteRequest, current_user: dict = Depends(require_role("moderator"))):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("UPDATE users SET is_muted = 0, mute_reason = NULL WHERE id = ?", (req.user_id,))
    log_action(conn, current_user["id"], "unmute", req.user_id, "")
    conn.commit()
    conn.close()
    return {"success": True}

@router.post("/give-elo")
def give_elo(req: EloRequest, current_user: dict = Depends(require_role("moderator"))):
    """Give or take ELO for a game result (positive or negative)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    target = conn.execute("SELECT * FROM users WHERE id = ?", (req.user_id,)).fetchone()
    if not target:
        conn.close()
        raise HTTPException(404, "User not found")
    check_can_target(current_user, target["role"])
    conn.execute(
        "UPDATE users SET elo = MAX(0, elo + ?) WHERE id = ?", (req.elo, req.user_id)
    )
    log_action(conn, current_user["id"], "give_elo", req.user_id,
               f"ELO change: {req.elo:+d}. Reason: {req.reason}")
    conn.commit()
    conn.close()
    return {"success": True, "elo_change": req.elo}

# --- ADMIN ACTIONS ---

@router.post("/ban")
def ban_user(req: BanRequest, current_user: dict = Depends(require_role("admin"))):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    target = conn.execute("SELECT * FROM users WHERE id = ?", (req.user_id,)).fetchone()
    if not target:
        conn.close()
        raise HTTPException(404, "User not found")
    check_can_target(current_user, target["role"])
    conn.execute("UPDATE users SET is_banned = 1, ban_reason = ? WHERE id = ?", (req.reason, req.user_id))
    log_action(conn, current_user["id"], "ban", req.user_id, req.reason)
    conn.commit()
    conn.close()
    return {"success": True, "message": f"User banned: {req.reason}"}

@router.post("/unban")
def unban_user(req: BanRequest, current_user: dict = Depends(require_role("admin"))):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("UPDATE users SET is_banned = 0, ban_reason = NULL WHERE id = ?", (req.user_id,))
    log_action(conn, current_user["id"], "unban", req.user_id, "")
    conn.commit()
    conn.close()
    return {"success": True}

# --- DEVELOPER ACTIONS ---

@router.post("/set-elo")
def set_elo(req: EloRequest, current_user: dict = Depends(require_role("developer"))):
    """Directly set ELO to any value."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    target = conn.execute("SELECT * FROM users WHERE id = ?", (req.user_id,)).fetchone()
    if not target:
        conn.close()
        raise HTTPException(404, "User not found")
    old_elo = target["elo"]
    conn.execute("UPDATE users SET elo = ? WHERE id = ?", (max(0, req.elo), req.user_id))
    log_action(conn, current_user["id"], "set_elo", req.user_id,
               f"ELO: {old_elo} → {req.elo}. Reason: {req.reason}")
    conn.commit()
    conn.close()
    return {"success": True, "old_elo": old_elo, "new_elo": req.elo}

@router.post("/set-role")
def set_role(req: RoleRequest, current_user: dict = Depends(require_role("developer"))):
    valid_roles = ["player", "moderator", "admin", "developer"]
    if req.role not in valid_roles:
        raise HTTPException(400, f"Invalid role. Valid: {valid_roles}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    target = conn.execute("SELECT * FROM users WHERE id = ?", (req.user_id,)).fetchone()
    if not target:
        conn.close()
        raise HTTPException(404, "User not found")
    conn.execute("UPDATE users SET role = ? WHERE id = ?", (req.role, req.user_id))
    log_action(conn, current_user["id"], "set_role", req.user_id,
               f"Role: {target['role']} → {req.role}")
    conn.commit()
    conn.close()
    return {"success": True}

@router.get("/users")
def admin_get_users(current_user: dict = Depends(require_role("moderator"))):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    users = conn.execute("SELECT * FROM users ORDER BY elo DESC").fetchall()
    conn.close()
    return [dict(u) for u in users]

@router.get("/audit-log")
def audit_log(current_user: dict = Depends(require_role("admin"))):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    logs = conn.execute(
        """SELECT al.*, u1.username as admin_name, u2.username as target_name
           FROM audit_log al
           LEFT JOIN users u1 ON al.admin_id = u1.id
           LEFT JOIN users u2 ON al.target_user_id = u2.id
           ORDER BY al.created_at DESC LIMIT 200"""
    ).fetchall()
    conn.close()
    return [dict(l) for l in logs]

@router.get("/maps")
def get_maps(current_user: dict = Depends(require_role("moderator"))):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    maps = conn.execute("SELECT * FROM maps").fetchall()
    conn.close()
    return [dict(m) for m in maps]

@router.post("/maps")
def add_map(req: MapRequest, current_user: dict = Depends(require_role("developer"))):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("INSERT OR IGNORE INTO maps (name, image_url) VALUES (?, ?)", (req.name, req.image_url))
    log_action(conn, current_user["id"], "add_map", 0, f"Added map: {req.name}")
    conn.commit()
    conn.close()
    return {"success": True}

@router.delete("/maps/{map_name}")
def delete_map(map_name: str, current_user: dict = Depends(require_role("developer"))):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE maps SET active = 0 WHERE name = ?", (map_name,))
    conn.commit()
    conn.close()
    return {"success": True}

@router.get("/stats")
def admin_stats(current_user: dict = Depends(require_role("moderator"))):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    stats = {
        "total_users": conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"],
        "active_lobbies": conn.execute(
            "SELECT COUNT(*) as c FROM lobbies WHERE status IN ('waiting','picking','in_progress')"
        ).fetchone()["c"],
        "total_matches": conn.execute("SELECT COUNT(*) as c FROM matches").fetchone()["c"],
        "finished_matches": conn.execute(
            "SELECT COUNT(*) as c FROM matches WHERE status = 'finished'"
        ).fetchone()["c"],
        "banned_users": conn.execute("SELECT COUNT(*) as c FROM users WHERE is_banned = 1").fetchone()["c"],
        "top_player": None,
    }
    top = conn.execute(
        "SELECT username, elo FROM users WHERE is_banned = 0 ORDER BY elo DESC LIMIT 1"
    ).fetchone()
    if top:
        stats["top_player"] = dict(top)
    conn.close()
    return stats
