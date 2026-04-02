from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import sqlite3
import json
from database import DB_PATH
from auth_utils import get_current_user

router = APIRouter()

MAPS_POOL = ["Dust2", "Mirage", "Inferno", "Nuke", "Overpass", "Ancient", "Vertigo"]

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

class StartMatchRequest(BaseModel):
    lobby_id: int
    team: int  # 1 or 2

def get_lobby(conn, lobby_id):
    lobby = conn.execute("SELECT * FROM lobbies WHERE id = ?", (lobby_id,)).fetchone()
    if not lobby:
        raise HTTPException(404, "Lobby not found")
    d = dict(lobby)
    d["team1_ids"] = json.loads(d["team1_ids"] or "[]")
    d["team2_ids"] = json.loads(d["team2_ids"] or "[]")
    d["banned_maps"] = json.loads(d["banned_maps"] or "[]")
    d["picked_maps"] = json.loads(d["picked_maps"] or "[]")
    return d

def get_lobby_players(conn, lobby_id):
    players = conn.execute(
        """SELECT u.id, u.username, u.game_id, u.elo, u.avatar_color, u.role, lp.team
           FROM lobby_players lp JOIN users u ON lp.user_id = u.id
           WHERE lp.lobby_id = ?""", (lobby_id,)
    ).fetchall()
    return [dict(p) for p in players]

@router.get("/")
def list_lobbies():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    lobbies = conn.execute(
        "SELECT * FROM lobbies WHERE status IN ('waiting','picking') ORDER BY created_at DESC LIMIT 20"
    ).fetchall()
    result = []
    for lb in lobbies:
        d = dict(lb)
        count = conn.execute(
            "SELECT COUNT(*) as cnt FROM lobby_players WHERE lobby_id = ?", (d["id"],)
        ).fetchone()["cnt"]
        d["player_count"] = count
        result.append(d)
    conn.close()
    return result

@router.get("/{lobby_id}")
def get_lobby_detail(lobby_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    lobby = get_lobby(conn, lobby_id)
    players = get_lobby_players(conn, lobby_id)
    available_maps = [m for m in MAPS_POOL if m not in lobby["banned_maps"] and m not in lobby["picked_maps"]]
    lobby["players"] = players
    lobby["available_maps"] = available_maps
    conn.close()
    return lobby

@router.post("/create")
def create_lobby(req: CreateLobbyRequest, current_user: dict = Depends(get_current_user)):
    if current_user["is_banned"]:
        raise HTTPException(403, "You are banned")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Check user not already in active lobby
    existing = conn.execute(
        """SELECT lp.lobby_id FROM lobby_players lp
           JOIN lobbies l ON lp.lobby_id = l.id
           WHERE lp.user_id = ? AND l.status IN ('waiting','picking','in_progress')""",
        (current_user["id"],)
    ).fetchone()
    if existing:
        conn.close()
        raise HTTPException(400, "Already in a lobby")

    c = conn.cursor()
    c.execute(
        """INSERT INTO lobbies (name, created_by, captain1_id, team1_ids, team2_ids, banned_maps, picked_maps)
           VALUES (?, ?, ?, '[]', '[]', '[]', '[]')""",
        (req.name.strip(), current_user["id"], current_user["id"])
    )
    lobby_id = c.lastrowid

    # Creator joins team 1
    c.execute(
        "INSERT INTO lobby_players (lobby_id, user_id, team) VALUES (?, ?, 1)",
        (lobby_id, current_user["id"])
    )
    # Add to team1_ids
    c.execute(
        "UPDATE lobbies SET team1_ids = ? WHERE id = ?",
        (json.dumps([current_user["id"]]), lobby_id)
    )

    conn.commit()
    lobby = get_lobby(conn, lobby_id)
    players = get_lobby_players(conn, lobby_id)
    lobby["players"] = players
    lobby["available_maps"] = MAPS_POOL[:]
    conn.close()
    return lobby

@router.post("/join")
def join_lobby(req: JoinRequest, current_user: dict = Depends(get_current_user)):
    if current_user["is_banned"]:
        raise HTTPException(403, "You are banned")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    lobby = get_lobby(conn, req.lobby_id)

    if lobby["status"] != "waiting":
        conn.close()
        raise HTTPException(400, "Lobby is not open")

    players = get_lobby_players(conn, req.lobby_id)
    if len(players) >= 10:
        conn.close()
        raise HTTPException(400, "Lobby is full")

    already = any(p["id"] == current_user["id"] for p in players)
    if already:
        conn.close()
        raise HTTPException(400, "Already in this lobby")

    conn.execute(
        "INSERT INTO lobby_players (lobby_id, user_id, team) VALUES (?, ?, 0)",
        (req.lobby_id, current_user["id"])
    )
    conn.commit()

    players = get_lobby_players(conn, req.lobby_id)
    lobby = get_lobby(conn, req.lobby_id)
    lobby["players"] = players
    lobby["available_maps"] = [m for m in MAPS_POOL if m not in lobby["banned_maps"]]
    conn.close()
    return lobby

@router.post("/leave")
def leave_lobby(req: JoinRequest, current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    lobby = get_lobby(conn, req.lobby_id)

    if lobby["status"] not in ("waiting",):
        conn.close()
        raise HTTPException(400, "Cannot leave after picking started")

    conn.execute(
        "DELETE FROM lobby_players WHERE lobby_id = ? AND user_id = ?",
        (req.lobby_id, current_user["id"])
    )

    # Remove from team arrays
    for team_col in ("team1_ids", "team2_ids"):
        ids = lobby[team_col.replace("_ids", "")] if team_col == "team1_ids" else []
        ids = lobby["team1_ids"] if team_col == "team1_ids" else lobby["team2_ids"]
        if current_user["id"] in ids:
            ids.remove(current_user["id"])
            conn.execute(f"UPDATE lobbies SET {team_col} = ? WHERE id = ?",
                        (json.dumps(ids), req.lobby_id))

    conn.commit()
    conn.close()
    return {"success": True}

@router.post("/start-picking")
def start_picking(req: JoinRequest, current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    lobby = get_lobby(conn, req.lobby_id)

    if lobby["created_by"] != current_user["id"] and current_user["role"] not in ("admin", "developer"):
        conn.close()
        raise HTTPException(403, "Only lobby creator can start")

    players = get_lobby_players(conn, req.lobby_id)
    if len(players) < 2:
        conn.close()
        raise HTTPException(400, "Need at least 2 players")

    # Assign captains and unassigned players
    unassigned = [p for p in players if p["team"] == 0]
    for p in unassigned:
        conn.execute(
            "UPDATE lobby_players SET team = 0 WHERE lobby_id = ? AND user_id = ?",
            (req.lobby_id, p["id"])
        )

    conn.execute(
        "UPDATE lobbies SET status = 'picking', current_phase = 'ban', current_turn = 1 WHERE id = ?",
        (req.lobby_id,)
    )
    conn.commit()
    lobby = get_lobby(conn, req.lobby_id)
    players = get_lobby_players(conn, req.lobby_id)
    lobby["players"] = players
    lobby["available_maps"] = MAPS_POOL[:]
    conn.close()
    return lobby

@router.post("/pick-player")
def pick_player(req: PickPlayerRequest, current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    lobby = get_lobby(conn, req.lobby_id)

    if lobby["status"] != "picking":
        conn.close()
        raise HTTPException(400, "Lobby is not in picking phase")

    # Determine whose turn to pick
    turn = lobby["current_turn"]
    if turn == 1 and lobby["captain1_id"] != current_user["id"]:
        if current_user["role"] not in ("admin", "developer"):
            conn.close()
            raise HTTPException(403, "Not your turn to pick")
    if turn == 2 and lobby["captain2_id"] != current_user["id"]:
        if current_user["role"] not in ("admin", "developer"):
            conn.close()
            raise HTTPException(403, "Not your turn to pick")

    # Check player is unassigned
    player_row = conn.execute(
        "SELECT team FROM lobby_players WHERE lobby_id = ? AND user_id = ?",
        (req.lobby_id, req.player_id)
    ).fetchone()
    if not player_row or player_row["team"] != 0:
        conn.close()
        raise HTTPException(400, "Player not available")

    team_col = "team1_ids" if turn == 1 else "team2_ids"
    ids = lobby["team1_ids"] if turn == 1 else lobby["team2_ids"]
    ids.append(req.player_id)

    conn.execute(
        f"UPDATE lobbies SET {team_col} = ? WHERE id = ?",
        (json.dumps(ids), req.lobby_id)
    )
    conn.execute(
        "UPDATE lobby_players SET team = ? WHERE lobby_id = ? AND user_id = ?",
        (turn, req.lobby_id, req.player_id)
    )

    # Alternate turns
    next_turn = 2 if turn == 1 else 1
    conn.execute("UPDATE lobbies SET current_turn = ? WHERE id = ?", (next_turn, req.lobby_id))
    conn.commit()

    lobby = get_lobby(conn, req.lobby_id)
    players = get_lobby_players(conn, req.lobby_id)
    lobby["players"] = players
    lobby["available_maps"] = [m for m in MAPS_POOL if m not in lobby["banned_maps"]]
    conn.close()
    return lobby

@router.post("/set-captain2")
def set_captain2(req: PickPlayerRequest, current_user: dict = Depends(get_current_user)):
    """Lobby creator sets the captain for team 2."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    lobby = get_lobby(conn, req.lobby_id)

    if lobby["created_by"] != current_user["id"] and current_user["role"] not in ("admin", "developer"):
        conn.close()
        raise HTTPException(403, "Only creator can set captain 2")

    # Add captain2 to team2
    team2 = lobby["team2_ids"]
    if req.player_id not in team2:
        team2.append(req.player_id)

    conn.execute(
        "UPDATE lobbies SET captain2_id = ?, team2_ids = ? WHERE id = ?",
        (req.player_id, json.dumps(team2), req.lobby_id)
    )
    conn.execute(
        "UPDATE lobby_players SET team = 2 WHERE lobby_id = ? AND user_id = ?",
        (req.lobby_id, req.player_id)
    )
    conn.commit()
    lobby = get_lobby(conn, req.lobby_id)
    players = get_lobby_players(conn, req.lobby_id)
    lobby["players"] = players
    lobby["available_maps"] = MAPS_POOL[:]
    conn.close()
    return lobby

@router.post("/ban-map")
def ban_map(req: BanMapRequest, current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    lobby = get_lobby(conn, req.lobby_id)

    if lobby["status"] != "picking":
        conn.close()
        raise HTTPException(400, "Not in picking phase")
    if lobby["current_phase"] != "ban":
        conn.close()
        raise HTTPException(400, "Not in ban phase")

    turn = lobby["current_turn"]
    if turn == 1 and lobby["captain1_id"] != current_user["id"]:
        if current_user["role"] not in ("admin", "developer"):
            conn.close()
            raise HTTPException(403, "Not your turn")
    if turn == 2 and lobby["captain2_id"] != current_user["id"]:
        if current_user["role"] not in ("admin", "developer"):
            conn.close()
            raise HTTPException(403, "Not your turn")

    if req.map_name in lobby["banned_maps"] or req.map_name in lobby["picked_maps"]:
        conn.close()
        raise HTTPException(400, "Map already banned/picked")

    banned = lobby["banned_maps"]
    banned.append(req.map_name)
    ban_count = lobby["ban_count"] + 1
    next_turn = 2 if turn == 1 else 1

    # After 4 bans, switch to pick phase
    new_phase = lobby["current_phase"]
    if ban_count >= 4:
        new_phase = "pick"

    conn.execute(
        """UPDATE lobbies SET banned_maps = ?, ban_count = ?, current_turn = ?, current_phase = ?
           WHERE id = ?""",
        (json.dumps(banned), ban_count, next_turn, new_phase, req.lobby_id)
    )
    conn.commit()
    lobby = get_lobby(conn, req.lobby_id)
    players = get_lobby_players(conn, req.lobby_id)
    lobby["players"] = players
    lobby["available_maps"] = [m for m in MAPS_POOL if m not in lobby["banned_maps"] and m not in lobby["picked_maps"]]
    conn.close()
    return lobby

@router.post("/pick-map")
def pick_map(req: PickMapRequest, current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    lobby = get_lobby(conn, req.lobby_id)

    if lobby["status"] != "picking":
        conn.close()
        raise HTTPException(400, "Not in picking phase")
    if lobby["current_phase"] != "pick":
        conn.close()
        raise HTTPException(400, "Not in pick phase yet")

    if req.map_name in lobby["banned_maps"] or req.map_name in lobby["picked_maps"]:
        conn.close()
        raise HTTPException(400, "Map not available")

    picked = lobby["picked_maps"]
    picked.append(req.map_name)
    pick_count = lobby["pick_count"] + 1
    next_turn = 2 if lobby["current_turn"] == 1 else 1

    status = lobby["status"]
    map_val = lobby["map"]
    if pick_count >= 1:
        status = "in_progress"
        map_val = req.map_name

    conn.execute(
        """UPDATE lobbies SET picked_maps = ?, pick_count = ?, current_turn = ?, status = ?, map = ?
           WHERE id = ?""",
        (json.dumps(picked), pick_count, next_turn, status, map_val, req.lobby_id)
    )

    if status == "in_progress":
        # Create match record
        lobby_data = conn.execute("SELECT * FROM lobbies WHERE id = ?", (req.lobby_id,)).fetchone()
        conn.execute(
            """INSERT INTO matches (lobby_id, map, team1_ids, team2_ids)
               VALUES (?, ?, ?, ?)""",
            (req.lobby_id, map_val,
             lobby_data["team1_ids"], lobby_data["team2_ids"])
        )

    conn.commit()
    lobby = get_lobby(conn, req.lobby_id)
    players = get_lobby_players(conn, req.lobby_id)
    lobby["players"] = players
    lobby["available_maps"] = [m for m in MAPS_POOL if m not in lobby["banned_maps"] and m not in lobby["picked_maps"]]
    conn.close()
    return lobby
