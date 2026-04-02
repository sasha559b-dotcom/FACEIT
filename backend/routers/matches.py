from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import sqlite3
import json
from database import DB_PATH
from auth_utils import get_current_user, require_role

router = APIRouter()

class SubmitResultRequest(BaseModel):
    match_id: int
    winner: int  # 1 or 2
    score_team1: int = 0
    score_team2: int = 0

def calculate_elo(winner_elo: int, loser_elo: int, k: int = 25) -> tuple[int, int]:
    expected_win = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))
    winner_change = round(k * (1 - expected_win))
    loser_change = round(k * expected_win)
    return max(winner_change, 10), max(loser_change, 10)

@router.get("/")
def list_matches(limit: int = 20):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    matches = conn.execute(
        "SELECT * FROM matches ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(m) for m in matches]

@router.get("/{match_id}")
def get_match(match_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    match = conn.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
    if not match:
        raise HTTPException(404, "Match not found")
    d = dict(match)
    t1 = json.loads(d["team1_ids"] or "[]")
    t2 = json.loads(d["team2_ids"] or "[]")
    players1 = conn.execute(
        f"SELECT id, username, elo, avatar_color FROM users WHERE id IN ({','.join('?'*len(t1)) or '0'})", t1
    ).fetchall() if t1 else []
    players2 = conn.execute(
        f"SELECT id, username, elo, avatar_color FROM users WHERE id IN ({','.join('?'*len(t2)) or '0'})", t2
    ).fetchall() if t2 else []
    d["team1_players"] = [dict(p) for p in players1]
    d["team2_players"] = [dict(p) for p in players2]
    conn.close()
    return d

@router.post("/submit-result")
def submit_result(req: SubmitResultRequest, current_user: dict = Depends(require_role("moderator"))):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    match = conn.execute("SELECT * FROM matches WHERE id = ?", (req.match_id,)).fetchone()
    if not match:
        conn.close()
        raise HTTPException(404, "Match not found")
    if match["status"] == "finished":
        conn.close()
        raise HTTPException(400, "Match already finished")
    if req.winner not in (1, 2):
        conn.close()
        raise HTTPException(400, "Winner must be 1 or 2")

    t1 = json.loads(match["team1_ids"] or "[]")
    t2 = json.loads(match["team2_ids"] or "[]")

    winners = t1 if req.winner == 1 else t2
    losers = t2 if req.winner == 1 else t1

    # Average ELO for each team
    def avg_elo(ids):
        if not ids:
            return 1000
        rows = conn.execute(
            f"SELECT AVG(elo) as avg FROM users WHERE id IN ({','.join('?'*len(ids))})", ids
        ).fetchone()
        return rows["avg"] or 1000

    w_elo = avg_elo(winners)
    l_elo = avg_elo(losers)
    w_gain, l_loss = calculate_elo(int(w_elo), int(l_elo))

    for uid in winners:
        conn.execute(
            "UPDATE users SET elo = elo + ?, wins = wins + 1 WHERE id = ?", (w_gain, uid)
        )
    for uid in losers:
        conn.execute(
            "UPDATE users SET elo = MAX(0, elo - ?), losses = losses + 1 WHERE id = ?", (l_loss, uid)
        )

    from datetime import datetime
    conn.execute(
        """UPDATE matches SET winner = ?, score_team1 = ?, score_team2 = ?,
           status = 'finished', elo_change = ?, finished_at = ?
           WHERE id = ?""",
        (req.winner, req.score_team1, req.score_team2, w_gain,
         datetime.utcnow().isoformat(), req.match_id)
    )

    # Close lobby
    conn.execute(
        "UPDATE lobbies SET status = 'finished' WHERE id = ?", (match["lobby_id"],)
    )

    conn.execute(
        """INSERT INTO audit_log (admin_id, action, details)
           VALUES (?, 'submit_result', ?)""",
        (current_user["id"], f"Match {req.match_id}: team {req.winner} wins. +{w_gain}/-{l_loss} ELO")
    )

    conn.commit()
    conn.close()
    return {"success": True, "elo_change": {"winners": f"+{w_gain}", "losers": f"-{l_loss}"}}
