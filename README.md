# ⚡ FaceitTG — Telegram Mini App

Competitive 5v5 gaming platform inside Telegram.  
**База данных автоматически сохраняется в Telegram канал и восстанавливается при запуске.**

---

## 💾 Как работает сохранение БД

```
Запуск сервера
    → Ищет последний .db файл в Telegram канале
    → Скачивает и восстанавливает БД
    → Каждые 30 минут — автоматический бэкап в канал
    → При выключении — финальный бэкап
```

Все бэкапы выглядят так в канале:
```
💾 FaceitTG Backup
📅 20241215_143022
📝 Reason: auto (periodic)
📦 Size: 45056 bytes
[faceit_20241215_143022.db]
```

---

## 🚀 Настройка (один раз)

### 1. Создай Telegram бота
1. Напиши [@BotFather](https://t.me/BotFather) → `/newbot`
2. Скопируй **BOT_TOKEN**

### 2. Создай приватный канал для бэкапов
1. Telegram → Новый канал → **Приватный**
2. Добавь своего бота в канал как **администратора** (права на отправку файлов)
3. Узнай **CHANNEL_ID**:
   - Добавь [@getidsbot](https://t.me/getidsbot) в канал
   - Он напишет ID вида `-1001234567890`
   - Скопируй это число

### 3. Настрой переменные окружения

**Локально** — создай файл `backend/.env`:
```env
BOT_TOKEN=1234567890:ABCdef...
BACKUP_CHANNEL_ID=-1001234567890
DB_PATH=faceit.db
BACKUP_INTERVAL_SEC=1800
```

**На Railway** — в настройках сервиса добавь:
```
BOT_TOKEN        = 1234567890:ABCdef...
BACKUP_CHANNEL_ID = -1001234567890
DB_PATH          = faceit.db
```

---

## 🖥️ Запуск локально

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # заполни BOT_TOKEN и BACKUP_CHANNEL_ID
uvicorn main:app --reload --port 8000

# Frontend (другой терминал)
cd frontend
npm install
cp .env.example .env.local    # VITE_API_URL=http://localhost:8000/api
npm run dev
```

---

## 🚂 Деплой на Railway

1. Залей код на GitHub (все папки как в архиве)
2. [railway.app](https://railway.app) → **New Project → Deploy from GitHub**
3. Выбери репо
4. В настройках сервиса → **Variables** — добавь:
   ```
   BOT_TOKEN          = твой токен
   BACKUP_CHANNEL_ID  = id канала
   DB_PATH            = faceit.db
   ```
5. Deploy — готово!

При каждом деплое сервер сам найдёт последний бэкап в канале и восстановит данные.

---

## 🎮 Функции

| Роль | Что может |
|------|-----------|
| 🎮 Player | Играть, заходить в лобби |
| 🔵 Moderator | + Мут/анмут, выдача ELO за игру |
| 🛡️ Admin | + Бан/анбан, аудит лог |
| ⚡ Developer | + Всё: менять ELO, роли, карты |

**Первый зарегистрированный пользователь автоматически получает роль Developer.**

### Лобби (5v5)
1. Создаёшь лобби — становишься капитаном команды 1
2. До 10 игроков заходят
3. Назначаешь капитана команды 2
4. Запускаешь фазу пик/бан
5. **Бан карт** — по очереди баните (4 бана)
6. **Пик карты** — выбирается финальная карта
7. **Драфт игроков** — капитаны по очереди пикают
8. Идёте играть
9. Модератор вводит результат → ELO обновляется автоматически

---

## 📁 Структура проекта

```
faceit-tg/
├── backend/
│   ├── main.py          ← FastAPI + backup при старте/выключении
│   ├── database.py      ← SQLite схема
│   ├── tg_backup.py     ← Весь код бэкапа в Telegram
│   ├── auth_utils.py    ← Telegram auth
│   ├── requirements.txt
│   └── routers/
│       ├── auth.py
│       ├── users.py
│       ├── lobbies.py
│       ├── matches.py
│       └── admin.py
├── frontend/
│   └── src/
│       ├── pages/       ← Register, Home, Lobby, Leaderboard, Profile, Admin
│       └── components/
├── railway.toml
└── nixpacks.toml
```
