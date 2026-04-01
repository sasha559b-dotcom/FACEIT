"""
CYBER LEAGUE — Telegram Bot + FastAPI Mini App
Запуск: python bot.py
"""
import os, asyncio, logging, json, time, hashlib, hmac
from urllib.parse import parse_qsl

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo,
    MenuButtonWebApp
)
from aiogram.enums import ParseMode
import aiosqlite

# ── ENV ───────────────────────────────────────────────────────────────────────
BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
WEBAPP_URL  = os.getenv("WEBAPP_URL", "")          # https://your-app.up.railway.app
OWNER_ID    = int(os.getenv("OWNER_ID", "0"))      # ваш Telegram user_id
NEWS_CHAT   = os.getenv("NEWS_CHAT_ID", "")        # id группы для новостей (опционально)
DB_PATH     = os.getenv("DB_PATH", "cyberleague.db")
SECRET_KEY  = os.getenv("SECRET_KEY", "changeme")  # для верификации initData

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── DB ────────────────────────────────────────────────────────────────────────
async def get_db():
    return await aiosqlite.connect(DB_PATH)

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id INTEGER UNIQUE NOT NULL,
            nickname    TEXT NOT NULL,
            elo         INTEGER DEFAULT 1000,
            elo_5v5     INTEGER DEFAULT 1000,
            elo_2v2     INTEGER DEFAULT 1000,
            wins        INTEGER DEFAULT 0,
            losses      INTEGER DEFAULT 0,
            wins_5v5    INTEGER DEFAULT 0,
            losses_5v5  INTEGER DEFAULT 0,
            wins_2v2    INTEGER DEFAULT 0,
            losses_2v2  INTEGER DEFAULT 0,
            avg_5v5     REAL DEFAULT 0,
            avg_2v2     REAL DEFAULT 0,
            is_bot      INTEGER DEFAULT 0,
            registered  INTEGER DEFAULT 0,
            created_at  INTEGER DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS roles (
            user_id INTEGER PRIMARY KEY,
            role    TEXT NOT NULL DEFAULT 'player'
        );
        CREATE TABLE IF NOT EXISTS news (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            title   TEXT NOT NULL,
            body    TEXT NOT NULL,
            tag     TEXT DEFAULT '',
            pinned  INTEGER DEFAULT 0,
            ts      INTEGER DEFAULT (strftime('%s','now') * 1000)
        );
        CREATE TABLE IF NOT EXISTS matches (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            mode      TEXT DEFAULT '5v5',
            phase     TEXT DEFAULT 'pick',
            map       TEXT DEFAULT '',
            ct        TEXT DEFAULT '[]',
            t         TEXT DEFAULT '[]',
            chat_link TEXT DEFAULT '',
            status    TEXT DEFAULT 'active',
            winner    TEXT DEFAULT '',
            created_at INTEGER DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS lobbies (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            mode       TEXT DEFAULT '5v5',
            status     TEXT DEFAULT 'waiting',
            players    TEXT DEFAULT '[]',
            max_size   INTEGER DEFAULT 10,
            created_by INTEGER DEFAULT 0,
            created_at INTEGER DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS bans (
            user_id    INTEGER PRIMARY KEY,
            reason     TEXT DEFAULT '',
            banned_by  INTEGER DEFAULT 0,
            created_at INTEGER DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS medals (
            user_id    INTEGER NOT NULL,
            medal_id   TEXT NOT NULL,
            granted_by INTEGER DEFAULT 0,
            created_at INTEGER DEFAULT (strftime('%s','now')),
            PRIMARY KEY (user_id, medal_id)
        );
        """)
        # Создаём owner если задан
        if OWNER_ID:
            await db.execute(
                "INSERT OR IGNORE INTO roles(user_id,role) VALUES(?,?)",
                (OWNER_ID, "owner")
            )
        await db.commit()
    log.info("DB initialized")

# ── HELPERS ───────────────────────────────────────────────────────────────────
def verify_init_data(init_data: str) -> dict | None:
    """Верифицирует Telegram WebApp initData."""
    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
        hash_str = parsed.pop("hash", "")
        data_check = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        computed = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(computed, hash_str):
            user_data = json.loads(parsed.get("user", "{}"))
            return user_data
    except Exception:
        pass
    return None

async def get_role(user_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT role FROM roles WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
    return row[0] if row else "player"

async def is_banned(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM bans WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
    return bool(row)

def player_row(row) -> dict:
    keys = ["id","external_id","nickname","elo","elo_5v5","elo_2v2",
            "wins","losses","wins_5v5","losses_5v5","wins_2v2","losses_2v2",
            "avg_5v5","avg_2v2","is_bot","registered","created_at"]
    return dict(zip(keys, row))

# ── FASTAPI ───────────────────────────────────────────────────────────────────
app = FastAPI(title="CyberLeague API")

# Раздаём статику (webapp_admin.html → index.html)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/health")
async def health():
    return {"ok": True, "ts": int(time.time())}

# ── PLAYERS ──────────────────────────────────────────────────────────────────
@app.get("/api/players")
async def api_players():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM players ORDER BY elo_5v5 DESC") as cur:
            rows = await cur.fetchall()
    return [player_row(r) for r in rows]

@app.get("/api/player/{ext_id}")
async def api_player(ext_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM players WHERE external_id=?", (ext_id,)) as cur:
            row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Player not found")
    return player_row(row)

@app.post("/api/register")
async def api_register(req: Request):
    data = await req.json()
    user_id  = int(data.get("user_id", 0))
    nickname = str(data.get("nickname", "")).strip()[:32]
    if not user_id or not nickname:
        return JSONResponse({"ok": False, "error": "Missing fields"})
    if await is_banned(user_id):
        return JSONResponse({"ok": False, "error": "Banned"})
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO players(external_id,nickname,registered) VALUES(?,?,1)",
                (user_id, nickname)
            )
            await db.commit()
        except aiosqlite.IntegrityError:
            return JSONResponse({"ok": False, "error": "Already registered"})
    return JSONResponse({"ok": True})

# ── TOP ───────────────────────────────────────────────────────────────────────
@app.get("/api/top")
async def api_top(mode: str = "5v5", limit: int = 50):
    col = "elo_5v5" if mode == "5v5" else "elo_2v2"
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            f"SELECT external_id,nickname,{col} as elo,wins,losses,avg_5v5,avg_2v2,is_bot "
            f"FROM players ORDER BY {col} DESC LIMIT ?", (limit,)
        ) as cur:
            rows = await cur.fetchall()
    keys = ["external_id","nickname","elo","wins","losses","avg_5v5","avg_2v2","is_bot"]
    return [dict(zip(keys, r)) for r in rows]

# ── STATS ─────────────────────────────────────────────────────────────────────
@app.get("/api/stats")
async def api_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM players") as cur:
            total_players = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM matches") as cur:
            total_matches = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM matches WHERE status='active'") as cur:
            active_matches = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM lobbies WHERE status='waiting'") as cur:
            open_lobbies = (await cur.fetchone())[0]
    return {"total_players": total_players, "total_matches": total_matches,
            "active_matches": active_matches, "open_lobbies": open_lobbies}

# ── MATCHES ───────────────────────────────────────────────────────────────────
@app.get("/api/matches")
async def api_matches(status: str = "active"):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id,mode,phase,map,ct,t,chat_link,status,winner,created_at "
            "FROM matches WHERE status=? ORDER BY created_at DESC LIMIT 30", (status,)
        ) as cur:
            rows = await cur.fetchall()
    result = []
    for r in rows:
        result.append({
            "id": r[0], "mode": r[1], "phase": r[2], "map": r[3],
            "ct": json.loads(r[4]), "t": json.loads(r[5]),
            "chat_link": r[6], "status": r[7], "winner": r[8], "created_at": r[9]
        })
    return result

@app.post("/api/match/result")
async def api_match_result(req: Request):
    data = await req.json()
    match_id = int(data.get("match_id", 0))
    winner   = str(data.get("winner", ""))  # "ct" | "t"
    if not match_id or winner not in ("ct", "t"):
        return JSONResponse({"ok": False, "error": "Bad params"})
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT ct,t,mode FROM matches WHERE id=?", (match_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            return JSONResponse({"ok": False, "error": "Match not found"})
        ct_ids = json.loads(row[0])
        t_ids  = json.loads(row[1])
        mode   = row[2]
        elo_col = "elo_5v5" if mode == "5v5" else "elo_2v2"
        wins_col = f"wins_{mode}"
        losses_col = f"losses_{mode}"
        winners = ct_ids if winner == "ct" else t_ids
        losers  = t_ids  if winner == "ct" else ct_ids
        ELO_GAIN = 25
        for uid in winners:
            await db.execute(
                f"UPDATE players SET {elo_col}={elo_col}+{ELO_GAIN}, elo=elo+{ELO_GAIN},"
                f" {wins_col}={wins_col}+1, wins=wins+1 WHERE external_id=?", (uid,))
        for uid in losers:
            await db.execute(
                f"UPDATE players SET {elo_col}=MAX(100,{elo_col}-{ELO_GAIN}), elo=MAX(100,elo-{ELO_GAIN}),"
                f" {losses_col}={losses_col}+1, losses=losses+1 WHERE external_id=?", (uid,))
        # Обновляем WR
        for uid in winners + losers:
            async with db.execute(
                f"SELECT {wins_col},{losses_col} FROM players WHERE external_id=?", (uid,)
            ) as cur2:
                wr_row = await cur2.fetchone()
            if wr_row:
                w, l = wr_row
                total = w + l
                avg = round(w / total * 100, 1) if total else 0
                avg_col = f"avg_{mode}"
                await db.execute(f"UPDATE players SET {avg_col}=? WHERE external_id=?", (avg, uid))
        await db.execute("UPDATE matches SET status='finished',winner=? WHERE id=?", (winner, match_id))
        await db.commit()
    return JSONResponse({"ok": True})

# ── LOBBIES ───────────────────────────────────────────────────────────────────
@app.get("/api/lobbies")
async def api_lobbies():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id,mode,status,players,max_size,created_by,created_at "
            "FROM lobbies WHERE status='waiting' ORDER BY created_at DESC"
        ) as cur:
            rows = await cur.fetchall()
    result = []
    for r in rows:
        players = json.loads(r[3])
        result.append({
            "id": r[0], "mode": r[1], "status": r[2],
            "players": players, "player_count": len(players),
            "max_size": r[4], "created_by": r[5], "created_at": r[6]
        })
    return result

@app.post("/api/lobby/join")
async def api_lobby_join(req: Request):
    data = await req.json()
    lobby_id = int(data.get("lobby_id", 0))
    user_id  = int(data.get("user_id", 0))
    if not lobby_id or not user_id:
        return JSONResponse({"ok": False, "error": "Missing fields"})
    if await is_banned(user_id):
        return JSONResponse({"ok": False, "error": "You are banned"})
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT players,max_size,status FROM lobbies WHERE id=?", (lobby_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            return JSONResponse({"ok": False, "error": "Lobby not found"})
        players, max_size, status = json.loads(row[0]), row[1], row[2]
        if status != "waiting":
            return JSONResponse({"ok": False, "error": "Lobby closed"})
        if user_id in players:
            return JSONResponse({"ok": False, "error": "Already in lobby"})
        if len(players) >= max_size:
            return JSONResponse({"ok": False, "error": "Lobby full"})
        players.append(user_id)
        new_status = "ready" if len(players) >= max_size else "waiting"
        await db.execute("UPDATE lobbies SET players=?,status=? WHERE id=?",
                         (json.dumps(players), new_status, lobby_id))
        await db.commit()
    return JSONResponse({"ok": True, "player_count": len(players), "status": new_status})

@app.post("/api/lobby/leave")
async def api_lobby_leave(req: Request):
    data = await req.json()
    lobby_id = int(data.get("lobby_id", 0))
    user_id  = int(data.get("user_id", 0))
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT players FROM lobbies WHERE id=?", (lobby_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            return JSONResponse({"ok": False, "error": "Lobby not found"})
        players = json.loads(row[0])
        if user_id in players:
            players.remove(user_id)
        await db.execute("UPDATE lobbies SET players=? WHERE id=?",
                         (json.dumps(players), lobby_id))
        await db.commit()
    return JSONResponse({"ok": True})

@app.post("/api/lobby/create")
async def api_lobby_create(req: Request):
    data = await req.json()
    mode       = str(data.get("mode", "5v5"))
    created_by = int(data.get("created_by", 0))
    max_size   = 10 if mode == "5v5" else 4
    if await is_banned(created_by):
        return JSONResponse({"ok": False, "error": "Banned"})
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO lobbies(mode,players,max_size,created_by) VALUES(?,?,?,?)",
            (mode, json.dumps([created_by]), max_size, created_by)
        )
        lobby_id = cur.lastrowid
        await db.commit()
    return JSONResponse({"ok": True, "lobby_id": lobby_id})

# ── NEWS ──────────────────────────────────────────────────────────────────────
@app.get("/api/news")
async def api_news():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id,title,body,tag,pinned,ts FROM news ORDER BY pinned DESC, ts DESC LIMIT 50"
        ) as cur:
            rows = await cur.fetchall()
    return [{"id":r[0],"title":r[1],"body":r[2],"tag":r[3],"pinned":bool(r[4]),"ts":r[5]} for r in rows]

@app.post("/api/news")
async def api_post_news(req: Request):
    data   = await req.json()
    title  = str(data.get("title","")).strip()
    body   = str(data.get("body","")).strip()
    tag    = str(data.get("tag","")).strip()
    pinned = bool(data.get("pinned", False))
    if not title or not body:
        return JSONResponse({"ok": False, "error": "Missing fields"})
    ts = int(time.time() * 1000)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO news(title,body,tag,pinned,ts) VALUES(?,?,?,?,?)",
            (title, body, tag, int(pinned), ts)
        )
        await db.commit()
    # Отправить в Telegram группу если настроено
    if NEWS_CHAT and bot_instance:
        pin_mark = "📌 " if pinned else ""
        tag_mark = f"\n🏷 #{tag}" if tag else ""
        text = f"{pin_mark}📰 <b>{title}</b>\n\n{body}{tag_mark}"
        try:
            await bot_instance.send_message(NEWS_CHAT, text, parse_mode=ParseMode.HTML)
        except Exception as e:
            log.warning(f"News broadcast error: {e}")
    return JSONResponse({"ok": True, "ts": ts})

@app.delete("/api/news/{news_id}")
async def api_delete_news(news_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM news WHERE id=?", (news_id,))
        await db.commit()
    return JSONResponse({"ok": True})

# ── ROLES ─────────────────────────────────────────────────────────────────────
@app.get("/api/roles")
async def api_roles():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id,role FROM roles") as cur:
            rows = await cur.fetchall()
    return {str(r[0]): r[1] for r in rows}

@app.post("/api/setrole")
async def api_setrole(req: Request):
    data    = await req.json()
    user_id = int(data.get("user_id", 0))
    role    = str(data.get("role", "player"))
    init_data = data.get("init_data", "")
    # Верификация — кто запрашивает
    requester_id = 0
    if init_data:
        user_obj = verify_init_data(init_data)
        if user_obj:
            requester_id = user_obj.get("id", 0)
    requester_role = await get_role(requester_id) if requester_id else "player"
    # owner может всё, admin не может назначать owner
    allowed_roles = ["player","moderator","admin"]
    if requester_role == "owner":
        allowed_roles.append("owner")
    if requester_role not in ("owner", "admin"):
        return JSONResponse({"ok": False, "error": "No permission"})
    if role not in allowed_roles:
        return JSONResponse({"ok": False, "error": "Invalid role"})
    if role == "player":
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM roles WHERE user_id=?", (user_id,))
            await db.commit()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO roles(user_id,role) VALUES(?,?)",
                (user_id, role)
            )
            await db.commit()
    return JSONResponse({"ok": True})

# ── BANS ──────────────────────────────────────────────────────────────────────
@app.post("/api/ban")
async def api_ban(req: Request):
    data    = await req.json()
    user_id = int(data.get("user_id", 0))
    reason  = str(data.get("reason", "")).strip()
    banned_by = int(data.get("banned_by", 0))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO bans(user_id,reason,banned_by) VALUES(?,?,?)",
            (user_id, reason, banned_by)
        )
        await db.commit()
    return JSONResponse({"ok": True})

@app.post("/api/unban")
async def api_unban(req: Request):
    data    = await req.json()
    user_id = int(data.get("user_id", 0))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM bans WHERE user_id=?", (user_id,))
        await db.commit()
    return JSONResponse({"ok": True})

@app.get("/api/bans")
async def api_bans():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id,reason,banned_by,created_at FROM bans") as cur:
            rows = await cur.fetchall()
    return [{"user_id":r[0],"reason":r[1],"banned_by":r[2],"created_at":r[3]} for r in rows]

# ── MEDALS ────────────────────────────────────────────────────────────────────
@app.get("/api/medals/{user_id}")
async def api_medals(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT medal_id FROM medals WHERE user_id=?", (user_id,)) as cur:
            rows = await cur.fetchall()
    return [r[0] for r in rows]

@app.post("/api/medals/grant")
async def api_grant_medal(req: Request):
    data      = await req.json()
    user_id   = int(data.get("user_id", 0))
    medal_id  = str(data.get("medal_id", ""))
    granted_by = int(data.get("granted_by", 0))
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT OR IGNORE INTO medals(user_id,medal_id,granted_by) VALUES(?,?,?)",
                (user_id, medal_id, granted_by)
            )
            await db.commit()
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e)})
    return JSONResponse({"ok": True})

@app.post("/api/medals/revoke")
async def api_revoke_medal(req: Request):
    data     = await req.json()
    user_id  = int(data.get("user_id", 0))
    medal_id = str(data.get("medal_id", ""))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM medals WHERE user_id=? AND medal_id=?", (user_id, medal_id))
        await db.commit()
    return JSONResponse({"ok": True})

# ── ADMIN: создание матча ─────────────────────────────────────────────────────
@app.post("/api/match/create")
async def api_match_create(req: Request):
    data = await req.json()
    mode      = str(data.get("mode", "5v5"))
    ct        = data.get("ct", [])
    t         = data.get("t", [])
    map_name  = str(data.get("map", ""))
    chat_link = str(data.get("chat_link", ""))
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO matches(mode,ct,t,map,chat_link,phase) VALUES(?,?,?,?,?,?)",
            (mode, json.dumps(ct), json.dumps(t), map_name, chat_link, "active")
        )
        match_id = cur.lastrowid
        await db.commit()
    return JSONResponse({"ok": True, "match_id": match_id})

# ── ELO adjust (admin) ────────────────────────────────────────────────────────
@app.post("/api/elo/adjust")
async def api_elo_adjust(req: Request):
    data    = await req.json()
    user_id = int(data.get("user_id", 0))
    delta   = int(data.get("delta", 0))
    mode    = str(data.get("mode", "5v5"))
    col     = "elo_5v5" if mode == "5v5" else "elo_2v2"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE players SET {col}=MAX(100,{col}+?), elo=MAX(100,elo+?) WHERE external_id=?",
            (delta, delta, user_id)
        )
        await db.commit()
    return JSONResponse({"ok": True})

# ─────────────────────────────────────────────────────────────────────────────
# TELEGRAM BOT
# ─────────────────────────────────────────────────────────────────────────────
bot_instance: Bot | None = None

def get_main_keyboard() -> ReplyKeyboardMarkup:
    url = WEBAPP_URL or "https://example.com"
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🎮 Открыть CYBER LEAGUE", web_app=WebAppInfo(url=url))]],
        resize_keyboard=True
    )

def make_bot_keyboard() -> InlineKeyboardMarkup:
    url = WEBAPP_URL or "https://example.com"
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎮 Открыть лигу", web_app=WebAppInfo(url=url))
    ]])

async def run_bot():
    global bot_instance
    if not BOT_TOKEN:
        log.warning("BOT_TOKEN not set — bot not started")
        return
    bot_instance = Bot(token=BOT_TOKEN)
    dp  = Dispatcher()

    # /start
    @dp.message(Command("start"))
    async def cmd_start(msg: types.Message):
        name = msg.from_user.first_name or "игрок"
        if WEBAPP_URL:
            await bot_instance.set_chat_menu_button(
                chat_id=msg.chat.id,
                menu_button=MenuButtonWebApp(text="🎮 Лига", web_app=WebAppInfo(url=WEBAPP_URL))
            )
        await msg.answer(
            f"👋 Привет, <b>{name}</b>!\n\n"
            "⚔️ <b>CYBER LEAGUE</b> — твоя платформа для соревновательных матчей.\n\n"
            "🎮 Жми кнопку ниже чтобы открыть Mini App!",
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_keyboard()
        )

    # /reg <nickname>
    @dp.message(Command("reg"))
    async def cmd_reg(msg: types.Message):
        parts = msg.text.split(maxsplit=1)
        if len(parts) < 2:
            await msg.answer("❌ Используй: /reg ТвойНикнейм")
            return
        nickname = parts[1].strip()[:32]
        user_id  = msg.from_user.id
        if await is_banned(user_id):
            await msg.answer("🚫 Ты забанен.")
            return
        async with aiosqlite.connect(DB_PATH) as db:
            try:
                await db.execute(
                    "INSERT INTO players(external_id,nickname,registered) VALUES(?,?,1)",
                    (user_id, nickname)
                )
                await db.commit()
            except aiosqlite.IntegrityError:
                await msg.answer("⚠️ Ты уже зарегистрирован! Используй /profile")
                return
        await msg.answer(
            f"✅ Зарегистрирован как <b>{nickname}</b>!\n"
            f"🆔 Твой Game ID: <code>{user_id}</code>\n\n"
            "Открывай лигу и смотри свой профиль! 🎮",
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_keyboard()
        )

    # /profile
    @dp.message(Command("profile"))
    async def cmd_profile(msg: types.Message):
        uid = msg.from_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT * FROM players WHERE external_id=?", (uid,)) as cur:
                row = await cur.fetchone()
        if not row:
            await msg.answer("❌ Ты не зарегистрирован. Используй /reg НикНейм")
            return
        p = player_row(row)
        role = await get_role(uid)
        role_str = {"owner":"👑 СОЗДАТЕЛЬ","admin":"⚙️ АДМИН","moderator":"🛡 МОДЕР","player":"🎮 ИГРОК"}.get(role,"🎮 ИГРОК")
        await msg.answer(
            f"👤 <b>{p['nickname']}</b> [{role_str}]\n"
            f"🆔 Game ID: <code>{p['external_id']}</code>\n\n"
            f"🏅 5v5 ELO: <b>{p['elo_5v5']}</b> | W/L: {p['wins_5v5']}/{p['losses_5v5']}\n"
            f"🏅 2v2 ELO: <b>{p['elo_2v2']}</b> | W/L: {p['wins_2v2']}/{p['losses_2v2']}",
            parse_mode=ParseMode.HTML,
            reply_markup=make_bot_keyboard()
        )

    # /top
    @dp.message(Command("top"))
    async def cmd_top(msg: types.Message):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT nickname,elo_5v5 FROM players ORDER BY elo_5v5 DESC LIMIT 10"
            ) as cur:
                rows = await cur.fetchall()
        if not rows:
            await msg.answer("Нет игроков.")
            return
        medals = ["🥇","🥈","🥉"] + [f"{i}." for i in range(4,11)]
        lines = [f"{medals[i]} <b>{r[0]}</b> — {r[1]} ELO" for i, r in enumerate(rows)]
        await msg.answer("🏆 <b>TOP-10 (5v5)</b>\n\n" + "\n".join(lines), parse_mode=ParseMode.HTML)

    # /lobby
    @dp.message(Command("lobby"))
    async def cmd_lobby(msg: types.Message):
        uid = msg.from_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT id,mode,players,max_size FROM lobbies WHERE status='waiting'"
            ) as cur:
                rows = await cur.fetchall()
        if not rows:
            await msg.answer(
                "Открытых лобби нет. Создай новое через Mini App! 🎮",
                reply_markup=make_bot_keyboard()
            )
            return
        lines = []
        for r in rows:
            ps = json.loads(r[2])
            lines.append(f"🎮 Лобби #{r[0]} [{r[1]}] — {len(ps)}/{r[3]} игроков")
        await msg.answer(
            "🎮 <b>Открытые лобби:</b>\n\n" + "\n".join(lines) + "\n\nВходи через Mini App!",
            parse_mode=ParseMode.HTML, reply_markup=make_bot_keyboard()
        )

    # /stats
    @dp.message(Command("stats"))
    async def cmd_stats(msg: types.Message):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM players") as cur:
                total_p = (await cur.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM matches") as cur:
                total_m = (await cur.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM lobbies WHERE status='waiting'") as cur:
                open_l = (await cur.fetchone())[0]
        await msg.answer(
            f"📊 <b>Статистика CYBER LEAGUE</b>\n\n"
            f"👥 Игроков: <b>{total_p}</b>\n"
            f"⚔️ Матчей: <b>{total_m}</b>\n"
            f"🎮 Открытых лобби: <b>{open_l}</b>",
            parse_mode=ParseMode.HTML
        )

    # /help
    @dp.message(Command("help"))
    async def cmd_help(msg: types.Message):
        await msg.answer(
            "📖 <b>Команды CYBER LEAGUE:</b>\n\n"
            "/start — Главное меню\n"
            "/reg НикНейм — Регистрация\n"
            "/profile — Мой профиль\n"
            "/top — Топ-10 игроков\n"
            "/lobby — Открытые лобби\n"
            "/stats — Статистика лиги\n"
            "/help — Эта справка",
            parse_mode=ParseMode.HTML
        )

    await dp.start_polling(bot_instance, allowed_updates=["message","callback_query"])

# ── MAIN ──────────────────────────────────────────────────────────────────────
async def main():
    await init_db()
    loop = asyncio.get_event_loop()
    # Запускаем бота в фоне
    if BOT_TOKEN:
        loop.create_task(run_bot())
    port = int(os.getenv("PORT", "8000"))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
