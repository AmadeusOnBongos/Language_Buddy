# Language_Buddy

A Telegram bot that helps you practice German (A1–A2) by chatting with you like a friendly language partner — and by reaching out to you first when you least expect it, so practice becomes a habit.

Built as an entry for the Gemma4 hackathon and as a hands-on project for learning LLMs, RAG, and backend deployment.

## What it currently does

- **Chats with you in German.** Write a message in German and the bot replies naturally, keeping the conversation going with questions.
- **Quietly corrects you.** Behind the scenes, a "reviewer" checks each of your messages for grammar and word-choice errors. The bot then works corrections into its reply — directly for major errors, more lightly for minor ones.
- **Message you first.** On a random schedule during waking hours (default 9:00–22:00), the bot sends you a German topic so you always have something to practice with.
- **Remembers the past.** It keeps a memory of previous conversations and uses them to pull up relevant context and avoid repeating old topics.

## Current status

- Everything above works locally (Windows/any Python 3.10+ machine).
- **Deployment is in progress** — Dockerizing and launching on your own server (VPS + webhook + HTTPS) is the next milestone. See the roadmap below.

## Getting started (run it yourself)

**Requirements:** Python 3.10+, a Telegram bot token, and an LLM API key.

1. Create a bot with [@BotFather](https://t.me/BotFather) on Telegram and paste the token into your project's `.env`.
2. Get an API key (default provider is [Groq](https://console.groq.com/); OpenAI is also supported via `LLM_PROVIDER`).
3. Install dependencies and start:

   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows (PowerShell); on Linux: source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env         # then fill in TELEGRAM_TOKEN and LLM_API_KEY
   python bot.py
   ```

4. Open your bot in Telegram, send `/start`, and just start typing in German. The bot will occasionally message you on its own, too.

All configuration (LLM model, difficulty level, schedule times/intervals, bot mode) lives in `.env` — see `.env.example`.

## How corrections work

- **Major errors** (meaning changes or the sentence becomes unintelligible) → corrected immediately and gently.
- **Minor errors** (articles, endings, etc.) → corrected lightly when appropriate, so the conversation doesn't turn into a grammar class.

## Roadmap

- [ ] **Local polish** — scheduler end-to-end verification, minor bug fixes, pinned dependencies
- [ ] **Dockerize** — container + compose setup with persistent storage
- [ ] **Deploy** — VPS + Docker + HTTPS webhook (Caddy), provider-agnostic so anyone can self-host
- [ ] **Future ideas** — practice streaks, a `/stop` quiet mode, and a small stats site

## For developers

Everything a developer/agent needs (architecture, conventions, gotchas, roadmap) is in [`AGENTS.md`](AGENTS.md).