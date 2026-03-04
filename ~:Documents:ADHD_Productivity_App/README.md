# 🧠 ADHD Productivity Hub

A full-featured ADHD productivity app built with Streamlit.

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the app

```bash
streamlit run app.py
```

The app will open at **http://localhost:8501** in your browser.

---

## Feature Overview

| Tab | What it does |
|-----|-------------|
| 🏠 Dashboard | Set energy level, Bad Brain Day mode, pick top priorities, quick capture, calendar preview, end-of-day review |
| ✅ Tasks | Add/manage tasks with priorities, categories, subtasks, Pomodoro counts, and habit tracking |
| 📝 Notes | Brain dump with optional AI analysis — extracts tags, summary, and action items |
| 📅 Calendar | Google Calendar integration, color-coded time blocks |
| 🍅 Pomodoro | In-browser countdown timer, session logging, 7-day focus chart |
| 👥 Accountability | Virtual partner sessions with progress tracking and reflection |

---

## AI Features Setup (Anthropic)

1. Run the app
2. Click **⚙️ Settings** in the top-right
3. Paste your Anthropic API key
4. Click **Save API Key**

AI features enabled:
- 🤖 **Note analysis** — auto-tags, summaries, and extracts action items
- 💡 **Task suggestions** — recommends tasks based on energy level

Get an API key at: https://console.anthropic.com/

---

## Google Calendar Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable the **Google Calendar API** (APIs & Services → Library → search "Google Calendar API")
4. Go to **Credentials** → **+ Create Credentials** → **OAuth 2.0 Client IDs**
5. Set Application Type to **Desktop app**, give it any name
6. Click **Download JSON** — rename the file to **`credentials.json`**
7. Move `credentials.json` into the same folder as `app.py`
8. In the app, go to the **📅 Calendar** tab and click **Connect Google Calendar**
9. A browser window will open — sign in and authorize the app
10. You're connected! ✅

**Note:** The first time you authorize, Google may show a warning about the app being unverified — this is normal for personal apps. Click "Advanced" → "Go to [app name]" to proceed.

---

## File Structure

```
ADHD_Productivity_App/
├── app.py              ← Main Streamlit app (run this)
├── db.py               ← SQLite database layer
├── ai_utils.py         ← Anthropic API integration
├── google_cal.py       ← Google Calendar integration
├── requirements.txt    ← Python dependencies
├── README.md           ← This file
├── adhd_app.db         ← SQLite database (created automatically)
├── credentials.json    ← Google OAuth credentials (you add this)
└── token.json          ← Google auth token (created automatically after connecting)
```

---

## Data Storage

All data is stored locally in `adhd_app.db` (SQLite). Nothing is sent to any server except:
- Notes/tasks sent to Anthropic API (only when you click Analyze or AI Suggest)
- Calendar events synced to your Google Calendar account

---

## Tips for ADHD Users

- **Start every morning** on the 🏠 Dashboard — set energy, toggle Bad Brain Day if needed, pick your top 3–5 priorities
- Use **Quick Capture** anywhere to offload thoughts instantly without breaking flow
- The **🍅 Pomodoro** tab pairs perfectly with the **👥 Accountability** tab
- **Brain Dump** in Notes is for anything — voice transcripts, half-formed thoughts, meeting rambles
- **Bad Brain Day mode** caps your task list at 3 and removes pressure — use it freely
