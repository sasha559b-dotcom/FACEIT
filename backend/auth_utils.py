import hmac
import hashlib
import json
import os
from urllib.parse import unquote
from fastapi import HTTPException, Header, Depends
import sqlite3
from database import get_db, DB_PATH

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

ROLE_HIERARCHY = {
    "player": 0,
    "moderator": 1,
    "admin": 2,
    "developer": 3,
}

def verify_telegram_init_data(init_data: str) -> dict:
    """Verify Telegram WebApp initData and return user info."""
    try:
        parsed = {}
        for part in init_data.split("&"):
            k, _, v = part.partition("=")
            parsed[k] = unquote(v)

        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items()) if k != "hash"
        )
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        computed = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        # In dev mode, skip hash check if BOT_TOKEN is placeholder
        if BOT_TOKEN != "YOUR_BOT_TOKEN_HERE":
            if computed != parsed.get("hash", ""):
                raise HTTPException(status_code=401, detail="Invalid Telegram data")

        user_data = json.loads(parsed.get("user", "{}"))
        return user_data
    except HTTPException:
        raise
    except Exception as e:
        # Dev fallback: parse user from raw JSON
        try:
            return json.loads(init_data)
        except:
            raise HTTPException(status_code=401, detail="Auth failed")


def get_current_user(
    x_init_data: str = Header(None),
    x_telegram_id: str = Header(None),
):
    """Get current user from DB based on Telegram auth."""
    telegram_id = None

    if x_init_data:
        try:
            tg_user = verify_telegram_init_data(x_init_data)
            telegram_id = str(tg_user.get("id", ""))
        except:
            pass

    if not telegram_id and x_telegram_id:
        telegram_id = x_telegram_id

    if not telegram_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    user = conn.execute(
        "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
    ).fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=404, detail="User not registered")

    return dict(user)


def require_role(min_role: str):
    """Dependency factory: require at least this role."""
    def checker(current_user: dict = Depends(get_current_user)):
        user_level = ROLE_HIERARCHY.get(current_user["role"], 0)
        required_level = ROLE_HIERARCHY.get(min_role, 0)
        if user_level < required_level:
            raise HTTPException(status_code=403, detail=f"Requires {min_role} or higher")
        return current_user
    return checker
