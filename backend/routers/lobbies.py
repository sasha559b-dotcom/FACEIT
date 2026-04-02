from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import json
from auth_utils import get_current_user

router = APIRouter()

MAPS_POOL = ["Dust2", "Mirage", "Inferno", "Nuke", "Overpass", "Ancient", "Vertigo"]

def get_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=RealDictCursor)

class CreateLobbyRequest(BaseModel):
    name: str

class JoinRequest(BaseModel):
    lobby_id: int

class BanMapRequest(BaseModel):
    lobby_id: int
    map_name: str

class PickMapRequest(BaseModel):
    lobby_id: int
    map_name: str

class PickPlayerRequest(BaseModel):
    lobby_id: int
    player_id: int

def get_lobby(cur, lobby_id):
    cur.execute("SELECT * FROM lobbies WHERE id = %s", (lobby_id,))
    lobby = cur.fetchone()
    if not lobby: raise HTTPException(404, "Lobby not found")
    d = dict(lobby)
    d["team1_ids"] = json.loads(d["team1_ids"] or "[]")
    d["team2_ids"] = json.loads(d["team2_ids"] or "[]")
    d["banned_maps"] = json.loads(d["banned_maps"] or "[]")
    d["picked_maps"] = json.loads(d["picked_maps"] or "[]")
    return d

def get_lobby_players(cur, lobby_id):
    cur.execute("""SELECT u.id, u.username, u.game_id, u.elo, u.avatar_color, u.role, lp.team
       FROM lobby_players lp JOIN users u ON lp.user_id = u.id
       WHERE lp.lobby_id = %s""", (lobby_id,))
    return [dict(p) for p in cur.fetchall()]

@router.get("/")
def list_lobbies():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM lobbies WHERE status IN ('waiting','picking') ORDER BY created_at DESC LIMIT 20")
    lobbies = cur.fetchall()
    result = []
    for lb in lobbies:
        d = dict(lb)
        cur.execute("SELECT COUNT(*) as cnt FROM lobby_players WHERE lobby_id = %s", (d["id"],))
        d["player_count"] = cur.fetchone()["cnt"]
        result.append(d)
    conn.close()
    return result

@router.get("/{lobby_id}")
def get_lobby_detail(lobby_id: int):
    conn = get_conn(); cur = conn.cursor()
    lobby = get_lobby(cur, lobby_id)
    players = get_lobby_players(cur, lobby_id)
    lobby["players"] = players
    lobby["available_maps"] = [m for m in MAPS_POOL if m not in lobby["banned_maps"] and m not in lobby["picked_maps"]]
    conn.close()
    return lobby

@router.post("/create")
def create_lobby(req: CreateLobbyRequest, current_user: dict = Depends(get_current_user)):
    if current_user["is_banned"]: raise HTTPException(403, "You are banned")
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""SELECT lp.lobby_id FROM lobby_players lp JOIN lobbies l ON lp.lobby_id = l.id
       WHERE lp.user_id = %s AND l.status IN ('waiting','picking','in_progress')""", (current_user["id"],))
    if cur.fetchone(): conn.close(); raise HTTPException(400, "Already in a lobby")

    cur.execute("""INSERT INTO lobbies (name, created_by, captain1_id, team1_ids, team2_ids, banned_maps, picked_maps)
       VALUES (%s, %s, %s, '[]', '[]', '[]', '[]') RETURNING id""",
        (req.name.strip(), current_user["id"], current_user["id"]))
    lobby_id = cur.fetchone()["id"]
    cur.execute("INSERT INTO lobby_players (lobby_id, user_id, team) VALUES (%s, %s, 1)", (lobby_id, current_user["id"]))
    cur.execute("UPDATE lobbies SET team1_ids = %s WHERE id = %s", (json.dumps([current_user["id"]]), lobby_id))
    conn.commit()
    lobby = get_lobby(cur, lobby_id)
    lobby["players"] = get_lobby_players(cur, lobby_id)
    lobby["available_maps"] = MAPS_POOL[:]
    conn.close()
    return lobby

@router.post("/join")
def join_lobby(req: JoinRequest, current_user: dict = Depends(get_current_user)):
    if current_user["is_banned"]: raise HTTPException(403, "You are banned")
    conn = get_conn(); cur = conn.cursor()
    lobby = get_lobby(cur, req.lobby_id)
    if lobby["status"] != "waiting": conn.close(); raise HTTPException(400, "Lobby is not open")
    players = get_lobby_players(cur, req.lobby_id)
    if len(players) >= 10: conn.close(); raise HTTPException(400, "Lobby is full")
    if any(p["id"] == current_user["id"] for p in players): conn.close(); raise HTTPException(400, "Already in this lobby")
    cur.execute("INSERT INTO lobby_players (lobby_id, user_id, team) VALUES (%s, %s, 0)", (req.lobby_id, current_user["id"]))
    conn.commit()
    lobby = get_lobby(cur, req.lobby_id)
    lobby["players"] = get_lobby_players(cur, req.lobby_id)
    lobby["available_maps"] = [m for m in MAPS_POOL if m not in lobby["banned_maps"]]
    conn.close()
    return lobby

@router.post("/leave")
def leave_lobby(req: JoinRequest, current_user: dict = Depends(get_current_user)):
    conn = get_conn(); cur = conn.cursor()
    lobby = get_lobby(cur, req.lobby_id)
    if lobby["status"] not in ("waiting",): conn.close(); raise HTTPException(400, "Cannot leave after picking started")
    cur.execute("DELETE FROM lobby_players WHERE lobby_id = %s AND user_id = %s", (req.lobby_id, current_user["id"]))
    for team_col, ids in [("team1_ids", lobby["team1_ids"]), ("team2_ids", lobby["team2_ids"])]:
        if current_user["id"] in ids:
            ids.remove(current_user["id"])
            cur.execute(f"UPDATE lobbies SET {team_col} = %s WHERE id = %s", (json.dumps(ids), req.lobby_id))
    conn.commit(); conn.close()
    return {"success": True}

@router.post("/start-picking")
def start_picking(req: JoinRequest, current_user: dict = Depends(get_current_user)):
    conn = get_conn(); cur = conn.cursor()
    lobby = get_lobby(cur, req.lobby_id)
    if lobby["created_by"] != current_user["id"] and current_user["role"] not in ("admin", "developer"):
        conn.close(); raise HTTPException(403, "Only lobby creator can start")
    players = get_lobby_players(cur, req.lobby_id)
    if len(players) < 2: conn.close(); raise HTTPException(400, "Need at least 2 players")
    cur.execute("UPDATE lobbies SET status = 'picking', current_phase = 'ban', current_turn = 1 WHERE id = %s", (req.lobby_id,))
    conn.commit()
    lobby = get_lobby(cur, req.lobby_id)
    lobby["players"] = get_lobby_players(cur, req.lobby_id)
    lobby["available_maps"] = MAPS_POOL[:]
    conn.close()
    return lobby

@router.post("/ban-map")
def ban_map(req: BanMapRequest, current_user: dict = Depends(get_current_user)):
    conn = get_conn(); cur = conn.cursor()
    lobby = get_lobby(cur, req.lobby_id)
    if lobby["status"] != "picking": conn.close(); raise HTTPException(400, "Not in picking phase")
    if lobby["current_phase"] != "ban": conn.close(); raise HTTPException(400, "Not in ban phase")
    turn = lobby["current_turn"]
    if turn == 1 and lobby["captain1_id"] != current_user["id"] and current_user["role"] not in ("admin", "developer"):
        conn.close(); raise HTTPException(403, "Not your turn")
    if turn == 2 and lobby["captain2_id"] != current_user["id"] and current_user["role"] not in ("admin", "developer"):
        conn.close(); raise HTTPException(403, "Not your turn")
    if req.map_name in lobby["banned_maps"] or req.map_name in lobby["picked_maps"]:
        conn.close(); raise HTTPException(400, "Map already banned/picked")
    banned = lobby["banned_maps"] + [req.map_name]
    ban_count = lobby["ban_count"] + 1
    next_turn = 2 if turn == 1 else 1
    new_phase = "pick" if ban_count >= 4 else "ban"
    cur.execute("UPDATE lobbies SET banned_maps = %s, ban_count = %s, current_turn = %s, current_phase = %s WHERE id = %s",
        (json.dumps(banned), ban_count, next_turn, new_phase, req.lobby_id))
    conn.commit()
    lobby = get_lobby(cur, req.lobby_id)
    lobby["players"] = get_lobby_players(cur, req.lobby_id)
    lobby["available_maps"] = [m for m in MAPS_POOL if m not in lobby["banned_maps"] and m not in lobby["picked_maps"]]
    conn.close()
    return lobby

@router.post("/pick-map")
def pick_map(req: PickMapRequest, current_user: dict = Depends(get_current_user)):
    conn = get_conn(); cur = conn.cursor()
    lobby = get_lobby(cur, req.lobby_id)
    if lobby["status"] != "picking": conn.close(); raise HTTPException(400, "Not in picking phase")
    if lobby["current_phase"] != "pick": conn.close(); raise HTTPException(400, "Not in pick phase yet")
    if req.map_name in lobby["banned_maps"] or req.map_name in lobby["picked_maps"]:
        conn.close(); raise HTTPException(400, "Map not available")
    picked = lobby["picked_maps"] + [req.map_name]
    pick_count = lobby["pick_count"] + 1
    next_turn = 2 if lobby["current_turn"] == 1 else 1
    status = "in_progress" if pick_count >= 1 else lobby["status"]
    map_val = req.map_name if pick_count >= 1 else lobby["map"]
    cur.execute("UPDATE lobbies SET picked_maps = %s, pick_count = %s, current_turn = %s, status = %s, map = %s WHERE id = %s",
        (json.dumps(picked), pick_count, next_turn, status, map_val, req.lobby_id))
    if status == "in_progress":
        cur.execute("SELECT team1_ids, team2_ids FROM lobbies WHERE id = %s", (req.lobby_id,))
        lb = cur.fetchone()
        cur.execute("INSERT INTO matches (lobby_id, map, team1_ids, team2_ids) VALUES (%s, %s, %s, %s)",
            (req.lobby_id, map_val, lb["team1_ids"], lb["team2_ids"]))
    conn.commit()
    lobby = get_lobby(cur, req.lobby_id)
    lobby["players"] = get_lobby_players(cur, req.lobby_id)
    lobby["available_maps"] = [m for m in MAPS_POOL if m not in lobby["banned_maps"] and m not in lobby["picked_maps"]]
    conn.close()
    return lobby
