from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import json
from auth_utils import get_current_user, require_role

router = APIRouter()

def get_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=RealDictCursor)

class SubmitResultRequest(BaseModel):
    match_id: int
    winner: int
    score_team1: int = 0
    score_team2: int = 0

def calculate_elo(winner_elo, loser_elo, k=25):
    expected_win = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))
    winner_change = round(k * (1 - expected_win))
    loser_change = round(k * expected_win)
    return max(winner_change, 10), max(loser_change, 10)

@router.get("/")
def list_matches(limit: int = 20):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM matches ORDER BY created_at DESC LIMIT %s", (limit,))
    matches = cur.fetchall(); conn.close()
    return [dict(m) for m in matches]

@router.get("/{match_id}")
def get_match(match_id: int):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM matches WHERE id = %s", (match_id,))
    match = cur.fetchone()
    if not match: conn.close(); raise HTTPException(404, "Match not found")
    d = dict(match)
    t1 = json.loads(d["team1_ids"] or "[]")
    t2 = json.loads(d["team2_ids"] or "[]")
    if t1:
        cur.execute("SELECT id, username, elo, avatar_color FROM users WHERE id = ANY(%s)", (t1,))
        d["team1_players"] = [dict(p) for p in cur.fetchall()]
    else:
        d["team1_players"] = []
    if t2:
        cur.execute("SELECT id, username, elo, avatar_color FROM users WHERE id = ANY(%s)", (t2,))
        d["team2_players"] = [dict(p) for p in cur.fetchall()]
    else:
        d["team2_players"] = []
    conn.close()
    return d

@router.post("/submit-result")
def submit_result(req: SubmitResultRequest, current_user: dict = Depends(require_role("moderator"))):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM matches WHERE id = %s", (req.match_id,))
    match = cur.fetchone()
    if not match: conn.close(); raise HTTPException(404, "Match not found")
    if match["status"] == "finished": conn.close(); raise HTTPException(400, "Match already finished")
    if req.winner not in (1, 2): conn.close(); raise HTTPException(400, "Winner must be 1 or 2")

    t1 = json.loads(match["team1_ids"] or "[]")
    t2 = json.loads(match["team2_ids"] or "[]")
    winners = t1 if req.winner == 1 else t2
    losers = t2 if req.winner == 1 else t1

    def avg_elo(ids):
        if not ids: return 1000
        cur.execute("SELECT AVG(elo) as avg FROM users WHERE id = ANY(%s)", (ids,))
        return cur.fetchone()["avg"] or 1000

    w_elo = avg_elo(winners); l_elo = avg_elo(losers)
    w_gain, l_loss = calculate_elo(int(w_elo), int(l_elo))

    if winners:
        cur.execute("UPDATE users SET elo = elo + %s, wins = wins + 1 WHERE id = ANY(%s)", (w_gain, winners))
    if losers:
        cur.execute("UPDATE users SET elo = GREATEST(0, elo - %s), losses = losses + 1 WHERE id = ANY(%s)", (l_loss, losers))

    from datetime import datetime
    cur.execute(
        "UPDATE matches SET winner = %s, score_team1 = %s, score_team2 = %s, status = 'finished', elo_change = %s, finished_at = %s WHERE id = %s",
        (req.winner, req.score_team1, req.score_team2, w_gain, datetime.utcnow(), req.match_id)
    )
    cur.execute("UPDATE lobbies SET status = 'finished' WHERE id = %s", (match["lobby_id"],))
    cur.execute(
        "INSERT INTO audit_log (admin_id, action, details) VALUES (%s, 'submit_result', %s)",
        (current_user["id"], f"Match {req.match_id}: team {req.winner} wins. +{w_gain}/-{l_loss} ELO")
    )
    conn.commit(); conn.close()
    return {"success": True, "elo_change": {"winners": f"+{w_gain}", "losers": f"-{l_loss}"}}
