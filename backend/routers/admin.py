from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from auth_utils import get_current_user, require_role

router = APIRouter()

def get_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=RealDictCursor)

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
    role: str

class MapRequest(BaseModel):
    name: str
    image_url: str = ""

ROLE_HIERARCHY = {"player": 0, "moderator": 1, "admin": 2, "developer": 3}

def log_action(cur, admin_id, action, target_id, details=""):
    cur.execute(
        "INSERT INTO audit_log (admin_id, action, target_user_id, details) VALUES (%s, %s, %s, %s)",
        (admin_id, action, target_id, details)
    )

def check_can_target(actor, target_role):
    if ROLE_HIERARCHY.get(actor["role"], 0) <= ROLE_HIERARCHY.get(target_role, 0):
        raise HTTPException(403, "Cannot perform action on user with equal or higher role")

@router.post("/mute")
def mute_user(req: MuteRequest, current_user: dict = Depends(require_role("moderator"))):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (req.user_id,))
    target = cur.fetchone()
    if not target: conn.close(); raise HTTPException(404, "User not found")
    check_can_target(current_user, target["role"])
    cur.execute("UPDATE users SET is_muted = 1, mute_reason = %s WHERE id = %s", (req.reason, req.user_id))
    log_action(cur, current_user["id"], "mute", req.user_id, req.reason)
    conn.commit(); conn.close()
    return {"success": True, "message": f"User muted: {req.reason}"}

@router.post("/unmute")
def unmute_user(req: MuteRequest, current_user: dict = Depends(require_role("moderator"))):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("UPDATE users SET is_muted = 0, mute_reason = NULL WHERE id = %s", (req.user_id,))
    log_action(cur, current_user["id"], "unmute", req.user_id, "")
    conn.commit(); conn.close()
    return {"success": True}

@router.post("/give-elo")
def give_elo(req: EloRequest, current_user: dict = Depends(require_role("moderator"))):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (req.user_id,))
    target = cur.fetchone()
    if not target: conn.close(); raise HTTPException(404, "User not found")
    check_can_target(current_user, target["role"])
    cur.execute("UPDATE users SET elo = GREATEST(0, elo + %s) WHERE id = %s", (req.elo, req.user_id))
    log_action(cur, current_user["id"], "give_elo", req.user_id, f"ELO change: {req.elo:+d}. Reason: {req.reason}")
    conn.commit(); conn.close()
    return {"success": True, "elo_change": req.elo}

@router.post("/ban")
def ban_user(req: BanRequest, current_user: dict = Depends(require_role("admin"))):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (req.user_id,))
    target = cur.fetchone()
    if not target: conn.close(); raise HTTPException(404, "User not found")
    check_can_target(current_user, target["role"])
    cur.execute("UPDATE users SET is_banned = 1, ban_reason = %s WHERE id = %s", (req.reason, req.user_id))
    log_action(cur, current_user["id"], "ban", req.user_id, req.reason)
    conn.commit(); conn.close()
    return {"success": True, "message": f"User banned: {req.reason}"}

@router.post("/unban")
def unban_user(req: BanRequest, current_user: dict = Depends(require_role("admin"))):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("UPDATE users SET is_banned = 0, ban_reason = NULL WHERE id = %s", (req.user_id,))
    log_action(cur, current_user["id"], "unban", req.user_id, "")
    conn.commit(); conn.close()
    return {"success": True}

@router.post("/set-elo")
def set_elo(req: EloRequest, current_user: dict = Depends(require_role("developer"))):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (req.user_id,))
    target = cur.fetchone()
    if not target: conn.close(); raise HTTPException(404, "User not found")
    old_elo = target["elo"]
    cur.execute("UPDATE users SET elo = %s WHERE id = %s", (max(0, req.elo), req.user_id))
    log_action(cur, current_user["id"], "set_elo", req.user_id, f"ELO: {old_elo} → {req.elo}. Reason: {req.reason}")
    conn.commit(); conn.close()
    return {"success": True, "old_elo": old_elo, "new_elo": req.elo}

@router.post("/set-role")
def set_role(req: RoleRequest, current_user: dict = Depends(require_role("developer"))):
    valid_roles = ["player", "moderator", "admin", "developer"]
    if req.role not in valid_roles:
        raise HTTPException(400, f"Invalid role. Valid: {valid_roles}")
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (req.user_id,))
    target = cur.fetchone()
    if not target: conn.close(); raise HTTPException(404, "User not found")
    cur.execute("UPDATE users SET role = %s WHERE id = %s", (req.role, req.user_id))
    log_action(cur, current_user["id"], "set_role", req.user_id, f"Role: {target['role']} → {req.role}")
    conn.commit(); conn.close()
    return {"success": True}

@router.get("/users")
def admin_get_users(current_user: dict = Depends(require_role("moderator"))):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY elo DESC")
    users = cur.fetchall(); conn.close()
    return [dict(u) for u in users]

@router.get("/audit-log")
def audit_log(current_user: dict = Depends(require_role("admin"))):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""SELECT al.*, u1.username as admin_name, u2.username as target_name
       FROM audit_log al
       LEFT JOIN users u1 ON al.admin_id = u1.id
       LEFT JOIN users u2 ON al.target_user_id = u2.id
       ORDER BY al.created_at DESC LIMIT 200""")
    logs = cur.fetchall(); conn.close()
    return [dict(l) for l in logs]

@router.get("/maps")
def get_maps(current_user: dict = Depends(require_role("moderator"))):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM maps")
    maps = cur.fetchall(); conn.close()
    return [dict(m) for m in maps]

@router.post("/maps")
def add_map(req: MapRequest, current_user: dict = Depends(require_role("developer"))):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("INSERT INTO maps (name, image_url) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING", (req.name, req.image_url))
    log_action(cur, current_user["id"], "add_map", 0, f"Added map: {req.name}")
    conn.commit(); conn.close()
    return {"success": True}

@router.delete("/maps/{map_name}")
def delete_map(map_name: str, current_user: dict = Depends(require_role("developer"))):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("UPDATE maps SET active = 0 WHERE name = %s", (map_name,))
    conn.commit(); conn.close()
    return {"success": True}

@router.get("/stats")
def admin_stats(current_user: dict = Depends(require_role("moderator"))):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM users"); total_users = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) as c FROM lobbies WHERE status IN ('waiting','picking','in_progress')"); active = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) as c FROM matches"); total_matches = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) as c FROM matches WHERE status = 'finished'"); finished = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) as c FROM users WHERE is_banned = 1"); banned = cur.fetchone()["c"]
    cur.execute("SELECT username, elo FROM users WHERE is_banned = 0 ORDER BY elo DESC LIMIT 1"); top = cur.fetchone()
    conn.close()
    return {"total_users": total_users, "active_lobbies": active, "total_matches": total_matches,
            "finished_matches": finished, "banned_users": banned, "top_player": dict(top) if top else None}
