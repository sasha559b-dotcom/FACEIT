import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from database import init_db
from tg_backup import download_db_from_telegram, upload_db_to_telegram
from routers import auth, users, lobbies, matches, admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BACKUP_INTERVAL = int(os.getenv("BACKUP_INTERVAL_SEC", 1800))  # 30 min default

async def auto_backup_loop():
    """Periodically saves DB to Telegram channel."""
    while True:
        await asyncio.sleep(BACKUP_INTERVAL)
        logger.info("⏰ Auto-backup triggered...")
        await upload_db_to_telegram(reason="auto (periodic)")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Restore DB from Telegram channel on startup
    logger.info("🔄 Looking for latest backup in Telegram channel...")
    restored = await download_db_from_telegram()
    if restored:
        logger.info("✅ DB restored from Telegram backup!")
    else:
        logger.info("📭 No backup found — fresh start")

    # 2. Init tables (safe if already exist)
    init_db()

    # 3. Upload startup snapshot
    await upload_db_to_telegram(reason="startup")

    # 4. Background auto-backup
    task = asyncio.create_task(auto_backup_loop())

    yield

    # 5. Final backup on shutdown
    logger.info("💾 Shutdown — saving final backup...")
    await upload_db_to_telegram(reason="shutdown")
    task.cancel()


app = FastAPI(title="FaceitTG API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,    prefix="/api/auth",    tags=["auth"])
app.include_router(users.router,   prefix="/api/users",   tags=["users"])
app.include_router(lobbies.router, prefix="/api/lobbies", tags=["lobbies"])
app.include_router(matches.router, prefix="/api/matches", tags=["matches"])
app.include_router(admin.router,   prefix="/api/admin",   tags=["admin"])

@app.get("/")
def root():
    return {"status": "ok", "service": "FaceitTG"}

@app.post("/api/backup/now")
async def force_backup():
    """Manually trigger a DB backup to Telegram."""
    ok = await upload_db_to_telegram(reason="manual")
    return {"success": ok}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
