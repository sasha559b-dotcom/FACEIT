import sqlite3
import os

DB_PATH = os.getenv("DATABASE_URL", "faceit.db").replace("sqlite:///", "")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id TEXT UNIQUE NOT NULL,
        username TEXT UNIQUE NOT NULL,
        game_id TEXT NOT NULL,
        elo INTEGER DEFAULT 1000,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        role TEXT DEFAULT 'player',  -- player, moderator, admin, developer
        is_banned INTEGER DEFAULT 0,
        is_muted INTEGER DEFAULT 0,
        ban_reason TEXT,
        mute_reason TEXT,
        avatar_color TEXT DEFAULT '#6366f1',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS lobbies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        status TEXT DEFAULT 'waiting',  -- waiting, picking, in_progress, finished
        map TEXT,
        captain1_id INTEGER,
        captain2_id INTEGER,
        team1_ids TEXT DEFAULT '[]',
        team2_ids TEXT DEFAULT '[]',
        banned_maps TEXT DEFAULT '[]',
        picked_maps TEXT DEFAULT '[]',
        current_phase TEXT DEFAULT 'ban',  -- ban, pick
        current_turn INTEGER DEFAULT 1,    -- 1 or 2
        ban_count INTEGER DEFAULT 0,
        pick_count INTEGER DEFAULT 0,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(created_by) REFERENCES users(id)
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS lobby_players (
        lobby_id INTEGER,
        user_id INTEGER,
        team INTEGER DEFAULT 0,  -- 0=unassigned, 1=team1, 2=team2
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(lobby_id, user_id),
        FOREIGN KEY(lobby_id) REFERENCES lobbies(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lobby_id INTEGER,
        map TEXT,
        team1_ids TEXT,
        team2_ids TEXT,
        winner INTEGER DEFAULT 0,  -- 0=not done, 1=team1, 2=team2
        score_team1 INTEGER DEFAULT 0,
        score_team2 INTEGER DEFAULT 0,
        elo_change INTEGER DEFAULT 25,
        status TEXT DEFAULT 'in_progress',  -- in_progress, finished
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        finished_at TIMESTAMP,
        FOREIGN KEY(lobby_id) REFERENCES lobbies(id)
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        action TEXT,
        target_user_id INTEGER,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS maps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        image_url TEXT,
        active INTEGER DEFAULT 1
    )""")

    # Default maps
    default_maps = [
        ("Dust2", "https://cdn.faceit.com/static/stats_assets/csgo/maps/dust2.jpg"),
        ("Mirage", "https://cdn.faceit.com/static/stats_assets/csgo/maps/mirage.jpg"),
        ("Inferno", "https://cdn.faceit.com/static/stats_assets/csgo/maps/inferno.jpg"),
        ("Nuke", "https://cdn.faceit.com/static/stats_assets/csgo/maps/nuke.jpg"),
        ("Overpass", "https://cdn.faceit.com/static/stats_assets/csgo/maps/overpass.jpg"),
        ("Ancient", "https://cdn.faceit.com/static/stats_assets/csgo/maps/ancient.jpg"),
        ("Vertigo", "https://cdn.faceit.com/static/stats_assets/csgo/maps/vertigo.jpg"),
    ]
    c.executemany(
        "INSERT OR IGNORE INTO maps (name, image_url) VALUES (?, ?)", default_maps
    )

    conn.commit()
    conn.close()
    print("✅ Database initialized")
