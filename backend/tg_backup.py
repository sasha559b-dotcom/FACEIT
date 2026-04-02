import os
import asyncio
import aiohttp
import aiofiles
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BACKUP_CHANNEL_ID = os.getenv("BACKUP_CHANNEL_ID", "")  # e.g. -1001234567890
DB_PATH = os.getenv("DB_PATH", "faceit.db")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
TG_FILE_API = f"https://api.telegram.org/file/bot{BOT_TOKEN}"


async def download_db_from_telegram() -> bool:
    """On startup: find the last backup file in the channel and download it."""
    if not BOT_TOKEN or not BACKUP_CHANNEL_ID:
        logger.warning("⚠️ BACKUP_CHANNEL_ID or BOT_TOKEN not set — skipping restore")
        return False

    try:
        async with aiohttp.ClientSession() as session:
            # Get last 20 messages from channel, find latest DB file
            async with session.get(f"{TG_API}/getUpdates", params={
                "allowed_updates": '["channel_post"]',
                "limit": 1,
                "offset": -1
            }) as r:
                pass  # just to warm up

            # Use getHistory via forwardMessages workaround — use getChatHistory
            async with session.post(f"{TG_API}/forwardMessage", json={
                "chat_id": BACKUP_CHANNEL_ID,
                "from_chat_id": BACKUP_CHANNEL_ID,
                "message_id": 999999999  # will fail but gives us latest message_id hint
            }) as r:
                err = await r.json()
                # Extract latest message_id from error
                import re
                match = re.search(r'message_id.*?(\d+)', str(err.get('description', '')))
                latest_id = int(match.group(1)) if match else 100

            # Search backwards for a document (db file)
            for msg_id in range(latest_id, max(latest_id - 200, 0), -1):
                async with session.post(f"{TG_API}/forwardMessage", json={
                    "chat_id": BACKUP_CHANNEL_ID,
                    "from_chat_id": BACKUP_CHANNEL_ID,
                    "message_id": msg_id
                }) as r:
                    data = await r.json()
                    if data.get("ok"):
                        fwd = data["result"]
                        # Delete the forwarded message
                        await session.post(f"{TG_API}/deleteMessage", json={
                            "chat_id": BACKUP_CHANNEL_ID,
                            "message_id": fwd["message_id"]
                        })
                        if "document" in fwd:
                            doc = fwd["document"]
                            if doc.get("file_name", "").endswith(".db"):
                                file_id = doc["file_id"]
                                logger.info(f"📥 Found backup: {doc['file_name']} (msg {msg_id})")
                                await _download_file(session, file_id)
                                return True

        logger.info("📭 No backup found in channel — starting fresh")
        return False

    except Exception as e:
        logger.error(f"❌ Restore failed: {e}")
        return False


async def _download_file(session: aiohttp.ClientSession, file_id: str):
    """Download a file by file_id and save as DB_PATH."""
    async with session.get(f"{TG_API}/getFile", params={"file_id": file_id}) as r:
        data = await r.json()
        file_path = data["result"]["file_path"]

    url = f"{TG_FILE_API}/{file_path}"
    async with session.get(url) as r:
        content = await r.read()

    async with aiofiles.open(DB_PATH, "wb") as f:
        await f.write(content)

    logger.info(f"✅ DB restored from Telegram ({len(content)} bytes)")


async def upload_db_to_telegram(reason: str = "auto") -> bool:
    """Upload current DB file to the backup channel."""
    if not BOT_TOKEN or not BACKUP_CHANNEL_ID:
        return False

    if not os.path.exists(DB_PATH):
        return False

    try:
        now = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"faceit_{now}.db"

        async with aiohttp.ClientSession() as session:
            async with aiofiles.open(DB_PATH, "rb") as f:
                content = await f.read()

            form = aiohttp.FormData()
            form.add_field("chat_id", str(BACKUP_CHANNEL_ID))
            form.add_field("caption",
                f"💾 *FaceitTG Backup*\n"
                f"📅 `{now}`\n"
                f"📝 Reason: `{reason}`\n"
                f"📦 Size: `{len(content)} bytes`",
                content_type="text/plain"
            )
            form.add_field("parse_mode", "Markdown")
            form.add_field(
                "document",
                content,
                filename=filename,
                content_type="application/octet-stream"
            )

            async with session.post(f"{TG_API}/sendDocument", data=form) as r:
                result = await r.json()
                if result.get("ok"):
                    logger.info(f"✅ DB backed up to Telegram: {filename}")
                    return True
                else:
                    logger.error(f"❌ Backup failed: {result}")
                    return False

    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        return False


# Synchronous wrappers for use in FastAPI lifespan
def sync_download_db():
    return asyncio.run(download_db_from_telegram())

def sync_upload_db(reason="auto"):
    return asyncio.run(upload_db_to_telegram(reason))
