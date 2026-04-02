# ⚡ FaceitTG — Telegram Mini App

Competitive 5v5 gaming platform inside Telegram. Full pick/ban system, ELO ranking, role management and admin tools.

---

## 🎮 Features

### Player Features
- **Registration** — nickname + in-game ID
- **ELO System** — starts at 1000, ranks from Iron to Grandmaster
- **Leaderboard** — top players ranked by ELO
- **Lobbies** — create/join 5v5 lobbies
- **Map Pick/Ban** — 4 bans → 1 pick, alternating captains
- **Player Drafting** — captains pick players for their teams
- **Match History** — view past matches and scores

### Role System
| Role | Permissions |
|------|------------|
| 🎮 Player | Play, join lobbies |
| 🔵 Moderator | Mute/unmute, give/take ELO for matches |
| 🛡️ Admin | + Ban/unban, audit log |
| ⚡ Developer | + Set exact ELO, set roles, manage maps |

> **First registered user automatically gets Developer role.**

### Admin Panel
- Search and manage all users
- Mute/unmute players
- Ban/unban players
- Adjust ELO (±25, ±50 or exact value)
- Assign roles
- Full audit log
- Platform statistics

---

## 🚀 Quick Start (Local)

### Prerequisites
- Python 3.11+
- Node.js 18+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))

### 1. Clone & setup backend

```bash
git clone https://github.com/YOUR_USERNAME/faceit-tg.git
cd faceit-tg/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env and add your BOT_TOKEN

# Run backend
uvicorn main:app --reload --port 8000
```

Backend will be available at `http://localhost:8000`  
API docs: `http://localhost:8000/docs`

### 2. Setup frontend

```bash
cd ../frontend

# Install dependencies
npm install

# Set environment
cp .env.example .env.local
# Edit .env.local: VITE_API_URL=http://localhost:8000/api

# Run dev server
npm run dev
```

Frontend will be at `http://localhost:5173`

---

## 📦 Deploy to Railway

### Backend on Railway

1. Push code to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Select your repo
4. Set environment variables:
   ```
   BOT_TOKEN=your_bot_token_here
   DATABASE_URL=sqlite:///faceit.db
   ```
5. Railway auto-detects Python and deploys

### Frontend (Vercel/Netlify/GitHub Pages)

```bash
cd frontend

# Set your Railway backend URL
echo "VITE_API_URL=https://your-app.railway.app/api" > .env.production

# Build
npm run build
# Dist folder is ready to deploy
```

**Or deploy frontend on Railway too:**
1. Create second Railway service in same project
2. Set root directory to `frontend`
3. Build command: `npm install && npm run build`
4. Start command: `npx serve dist -l $PORT`
5. Set `VITE_API_URL` env var

### Configure Telegram Bot

1. Create bot via [@BotFather](https://t.me/BotFather)
2. Send `/newbot`, follow instructions
3. Send `/setmenubutton` → set Web App URL to your frontend URL
4. Or use inline keyboard with Web App button

**Bot commands (optional):**
```
/start - Open FaceitTG
```

---

## 🏗️ Project Structure

```
faceit-tg/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── database.py          # SQLite setup & migrations
│   ├── auth_utils.py        # Telegram auth + role helpers
│   ├── requirements.txt
│   ├── .env.example
│   └── routers/
│       ├── auth.py          # Register, login
│       ├── users.py         # Profiles, leaderboard
│       ├── lobbies.py       # Create, join, pick/ban
│       ├── matches.py       # Results, ELO calculation
│       └── admin.py         # All admin actions
│
├── frontend/
│   ├── index.html           # Telegram WebApp SDK loaded here
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── src/
│       ├── App.jsx          # Routing, auth init
│       ├── api.js           # Axios + auth headers
│       ├── store.js         # Zustand global state
│       ├── index.css        # Design system / theme
│       ├── components/
│       │   ├── Layout.jsx   # Bottom nav bar
│       │   └── UI.jsx       # Avatar, Badge, Toast, Modal...
│       └── pages/
│           ├── RegisterPage.jsx
│           ├── HomePage.jsx
│           ├── LobbyListPage.jsx
│           ├── LobbyPage.jsx    # Full pick/ban UI
│           ├── LeaderboardPage.jsx
│           ├── ProfilePage.jsx
│           ├── MatchPage.jsx
│           └── AdminPage.jsx    # Full admin panel
│
├── railway.toml
├── nixpacks.toml
└── .gitignore
```

---

## 🎯 How Lobbies Work

1. **Create** — any player creates a lobby (becomes Team 1 captain)
2. **Join** — up to 10 players join
3. **Set Captain 2** — creator assigns Team 2 captain
4. **Start Pick/Ban** — creator starts the phase
5. **Map Bans** — captains alternate banning maps (4 total)
6. **Map Pick** — remaining map is picked (or captains pick 1)
7. **Player Draft** — captains alternate picking players
8. **Play** — go play on the selected map
9. **Submit Result** — moderator/admin/dev submits score
10. **ELO Updated** — automatic ELO calculation for all players

---

## 🔒 API Authentication

All API requests require one of:
- `x-init-data` header — Telegram WebApp `initData` string
- `x-telegram-id` header — Telegram user ID (fallback)

---

## 🎨 Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | React 18, Vite, Zustand, React Router |
| Styling | Tailwind CSS + custom CSS variables |
| Backend | Python 3.11, FastAPI |
| Database | SQLite (WAL mode) |
| Auth | Telegram WebApp initData verification |
| Deploy | Railway (backend), Vercel/Railway (frontend) |

---

## 📝 License

MIT
