# AGENTS.md

Project guide for AI agents (and humans) working on **Language_Buddy**. Read this before making changes so you start up to speed without re-exploring everything.

## What this is

A Telegram bot that helps the owner practice German (A1–A2 level). It does two things:

1. **Converses** — the user writes in German, the bot replies like a friendly language partner, and a separate "reviewer" step quietly checks the user's messages for grammar/word-choice errors and folds corrections into the conversation.
2. **Proactively messages** — on a random schedule during waking hours (default 9:00–22:00), it sends a German topic/question to keep the user in the habit of daily practice.

Origin/purpose: built for the Gemma4 hackathon; also a vehicle to learn LLMs, RAG, and (now) backend deployment. Learning-oriented: the owner wants the project built **incrementally**, not all at once.

## Current status

### Done and working locally
- Telegram bot core (`bot.py`): `/start`, `/bye`, free-text handling.
- Two-stage LLM pipeline per message (`conversation.py`):
  1. **Reviewer** — parses the user's message for errors, returns JSON (`topic`, `has_errors`, `errors[]` with German + English explanations).
  2. **Converser** — builds a natural German reply, injecting corrections (mainly for major errors) and past context.
- RAG memory (`memory_store.py`): ChromaDB (persistent `./chroma_data/`) + FastEmbed embeddings (`BAAI/bge-small-en-v1.5`); semantic search of past exchanges (top-k = `rag_top_k`, default 5).
- LLM clients (`llm_client.py`): `GroqClient` (default) and `OpenAIClient`, behind a common `LLMClient` interface, selected by `LLM_PROVIDER`.
- Config via pydantic-settings from `.env` (`config.py`).
- Scheduler (`scheduler.py`): persists `chat_id` on `/start`; uses `Application.job_queue` to fire a random-interval proactive message (60–240 min), only inside the waking-hours window; generates topics via `ConversationManager.generate_topic()` (avoids repeating recent topics); reschedules itself.
- Webhook + polling modes both wired (`BOT_MODE`), webhook path uses the bot token as a secret.
- Phase 1 tidy-up (done): `get_recent_exchanges()` ordering fixed (fetch all → sort by timestamp → slice); `TIMEZONE` setting added (default `Europe/Berlin`, scheduler uses `ZoneInfo` + testable `is_waking_hours()`); `main.py` deleted; `run_bot.sh` fixed (`.venv`, strict mode, `exec`); `run_bot.ps1` + `run_bot.cmd` (double-click launcher for Windows) added; `requirements.txt` pinned; local `.venv` rebuilt; clean boot + scheduler firing verified in polling mode.

### Not done / planned (see roadmap at bottom)
- Deployment is **not** done. The owner's chosen path: **VPS + Docker + webhook behind Caddy (HTTPS)**. Verify locally first, then Dockerize, then add domain/HTTPS, then deploy. Keep everything provider-agnostic so other people can self-host too.
- Full scheduler loop (real topic *delivered* to the phone after `/start`) still needs a manual phone test — only the no-`chat_id` firing path has been verified in logs.
- Analytics is **designed but not implemented** (Postgres + capture now, Streamlit dashboard after deploy). The reviewer's `errors[]` is currently discarded — that's the main capture gap.
- No tests, no lint/typecheck config in the repo yet.

## Architecture / key files

| File | Role |
| --- | --- |
| `bot.py` | Telegram entrypoint (`python bot.py`). Sets up handlers, `conversation_manager`, scheduler. Stores manager in `app.bot_data` for the scheduler. |
| `conversation.py` | `ConversationManager`: `process_message()` (reviewer → converser → store), `generate_topic()`, `clear_history()`. In-memory per-chat history, last 20 messages. |
| `scheduler.py` | Proactive-message job: `save_chat_id`/`load_chat_id` (via `chat_id.txt`), `send_proactive_message`, `schedule_next`, `setup_scheduler`. |
| `llm_client.py` | `LLMClient` ABC + `GroqClient`/`OpenAIClient` + `get_llm_client()` factory. |
| `memory_store.py` | `MemoryStore`: ChromaDB collection + embedding; `add_exchange`, `search_similar`, `get_recent_exchanges`, `count`. |
| `prompts.py` | `REVIEWER_SYSTEM`, `CONVERSER_SYSTEM`, `TOPIC_GENERATOR` + prompt builders. |
| `config.py` | `Settings` (pydantic-settings), reads `.env`. |
| `dummy.py` | Scratch script for testing the Groq API directly. Not part of the app. |
| `run_bot.sh` | Linux launcher (`exec .venv/bin/python bot.py`). Fails fast with a clear error if `.venv` is missing. |
| `run_bot.ps1` | Windows launcher (same idea, via `.venv\Scripts\python.exe`). |
| `run_bot.cmd` | Double-clickable trampoline for Windows: calls `run_bot.ps1` with `-ExecutionPolicy Bypass`, pauses on failure so the window doesn't vanish. |
| `.env.example` | Template for config (copy to `.env`). |
| `TIMELINE.md` | Full project history, decisions, phase-by-phase plan, analytics design, consolidated gotchas. Read this after a long break. |

## Running locally

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows (PowerShell); on Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                # fill in TELEGRAM_TOKEN and LLM_API_KEY
python bot.py                       # starts in polling mode by default
```

Or skip the terminal: double-click `run_bot.cmd` on Windows, or run `./run_bot.sh` on Linux. Both launchers use `.venv` and fail with a clear error if it doesn't exist yet.

Environment: Windows dev machine + a Linux Mint laptop, **Python 3.10** (so the code's `int | None` / `str | None` syntax is fine, but ≥3.10 is required). Venv folder is standardized to **`.venv`** on all machines (both `venv/` and `.venv` are gitignored). `requirements.txt` is **pinned** (`==` versions, verified working together).

## Config (`config.py` / `.env`)

Key vars (full list in `.env.example` / `config.py`): `TELEGRAM_TOKEN`, `LLM_PROVIDER` (groq/openai), `LLM_MODEL` (default `llama-3.1-8b-instant`), `LLM_API_KEY`, `LLM_BASE_URL`, `GERMAN_LEVEL` (A1-A2), `TIMEZONE` (default `Europe/Berlin`), `RAG_*`, `EMBEDDING_MODEL`, `SCHEDULE_START_HOUR`/`SCHEDULE_END_HOUR`/`SCHEDULE_MIN/MAX_INTERVAL_MINUTES`, `BOT_MODE` (polling/webhook), `WEBHOOK_URL`/`WEBHOOK_PORT`, `REVIEWER_*`/`CONVERSER_TEMPERATURE`.

## Conventions

- Python 3.10+, plain modules (no package layout), stdlib + the deps in `requirements.txt`.
- Keep code comment-light, match existing style.
- Never commit secrets: `.env`, `chroma_data/`, `chat_id.txt`, `bot.log`, `.venv/` are gitignored.
- Preserve provider-agnosticism in any deploy artifacts (Docker, docs) so others can self-host on any VPS/Docker host.
- No test/lint/typecheck setup exists yet — don't invent one without asking the owner first. Run the bot manually to verify behavior (`python bot.py`, then talk to it in Telegram).

## Gotchas / watch-outs

- The scheduler's waking-hours check uses `ZoneInfo(settings.timezone)` (default `Europe/Berlin`). When deploying, make sure `TIMEZONE` matches the owner's wall clock — log timestamps themselves are still server-local.
- httpx logs full Telegram API URLs **including the bot token** into `bot.log` at INFO level. `bot.log` is gitignored, but never paste log excerpts publicly without redacting the token.
- `GroqClient` uses OpenAI's newer **`responses` API** (`input=` / `instructions=` kwargs), not `chat.completions`. Only `OpenAIClient` uses `chat.completions`. Don't "fix" one to look like the other unless intentional.
- Default model `llama-3.1-8b-instant` is older; Groq may retire/rename models. If it 404s, update `LLM_MODEL`.
- In-memory conversation history is lost on restart (kept per-process only); ChromaDB persists exchanges across restarts, but RAG is enabled by default while a chat is empty.
- The embedding model is English-focused (`bge-small-en`) but the content is largely German — quality limitation, acceptable for now.
- Webhook mode needs a real HTTPS endpoint (Telegram requires it). The reverse proxy must be added — this is the planned Caddy step.
- Proactive messages use a single `chat_id.txt` (personal-scale feature, one chat at a time).
- Windows dev shell is PowerShell (`run_bot.cmd` double-click); `run_bot.sh` is for the Linux Mint laptop.

## Documentation maintenance rules — IMPORTANT

1. **Update this `AGENTS.md` file every time a major feature is added or an important bug is fixed.** Keep status, architecture, config, and gotchas accurate. Don't wait for the owner to ask.
2. **Update `README.md` whenever a MAJOR feature or change is implemented** so the user-facing story stays current. (Minor fixes don't require a README change.)
3. **Keep `TIMELINE.md` current** — update its status snapshot and roadmap as phases advance. It is the durable project memory across sessions/workstations.

## Roadmap (incremental) — full detail in `TIMELINE.md`

1. **Verify locally & tidy** — DONE: scheduler firing verified in polling mode; `get_recent_exchanges()` ordering fixed; `main.py` deleted; `run_bot.sh` fixed + `run_bot.ps1`/`.cmd` added; `requirements.txt` pinned. Still open: manual phone test of a real delivered topic after `/start`.
2. **Postgres + capture + Dockerize** (NEXT) — add analytics capture first (`AnalyticsStore` on psycopg v3, `schema.sql`: sessions/exchanges/errors/proactive_messages, reviewer `category` field), then `Dockerfile`, `docker-compose.yml` (`bot` + `db`, volumes for Postgres/`DATA_DIR`/embedding cache, `TZ=Europe/Berlin`), `.dockerignore`.
3. **Webhook + HTTPS** — Caddy reverse proxy: `Caddy (443 public) → bot container (8443 private)`; `BOT_MODE=webhook`, `WEBHOOK_URL=https://<domain>`, `TZ=Europe/Berlin`; register webhook and verify via `getWebhookInfo`.
4. **Deploy** — provider-agnostic server setup (firewall 22/80/443, SSH keys, clone, `.env`, `docker compose up -d`, logs); full phone-to-bot loop test.
5. **Streamlit dashboard** — read-only Postgres views: activity/streak, session length, topic spread, errors by severity/category, nudge effectiveness.
6. **Polish** — deploy docs, optional Docker healthcheck, future ideas (streak stats, `/stop`-quiet mode, Chroma → pgvector consolidation).