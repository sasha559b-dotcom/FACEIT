import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL", "")

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        telegram_id TEXT UNIQUE NOT NULL,
        username TEXT UNIQUE NOT NULL,
        game_id TEXT NOT NULL,
        elo INTEGER DEFAULT 1000,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        role TEXT DEFAULT 'player',
        is_banned INTEGER DEFAULT 0,
        is_muted INTEGER DEFAULT 0,
        ban_reason TEXT,
        mute_reason TEXT,
        avatar_color TEXT DEFAULT '#6366f1',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS lobbies (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        status TEXT DEFAULT 'waiting',
        map TEXT,
        captain1_id INTEGER,
        captain2_id INTEGER,
        team1_ids TEXT DEFAULT '[]',
        team2_ids TEXT DEFAULT '[]',
        banned_maps TEXT DEFAULT '[]',
        picked_maps TEXT DEFAULT '[]',
        current_phase TEXT DEFAULT 'ban',
        current_turn INTEGER DEFAULT 1,
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
        team INTEGER DEFAULT 0,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(lobby_id, user_id),
        FOREIGN KEY(lobby_id) REFERENCES lobbies(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id SERIAL PRIMARY KEY,
        lobby_id INTEGER,
        map TEXT,
        team1_ids TEXT,
        team2_ids TEXT,
        winner INTEGER DEFAULT 0,
        score_team1 INTEGER DEFAULT 0,
        score_team2 INTEGER DEFAULT 0,
        elo_change INTEGER DEFAULT 25,
        status TEXT DEFAULT 'in_progress',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        finished_at TIMESTAMP,
        FOREIGN KEY(lobby_id) REFERENCES lobbies(id)
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id SERIAL PRIMARY KEY,
        admin_id INTEGER,
        action TEXT,
        target_user_id INTEGER,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS maps (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        image_url TEXT,
        active INTEGER DEFAULT 1
    )""")

    default_maps = [
        ("Dust2", "https://cdn.faceit.com/static/stats_assets/csgo/maps/dust2.jpg"),
        ("Mirage", "https://cdn.faceit.com/static/stats_assets/csgo/maps/mirage.jpg"),
        ("Inferno", "https://cdn.faceit.com/static/stats_assets/csgo/maps/inferno.jpg"),
        ("Nuke", "https://cdn.faceit.com/static/stats_assets/csgo/maps/nuke.jpg"),
        ("Overpass", "https://cdn.faceit.com/static/stats_assets/csgo/maps/overpass.jpg"),
        ("Ancient", "https://cdn.faceit.com/static/stats_assets/csgo/maps/ancient.jpg"),
        ("Vertigo", "https://cdn.faceit.com/static/stats_assets/csgo/maps/vertigo.jpg"),
    ]
    for name, url in default_maps:
        c.execute(
            "INSERT INTO maps (name, image_url) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING",
            (name, url)
        )

    conn.commit()
    conn.close()
    print("✅ Database initialized")
