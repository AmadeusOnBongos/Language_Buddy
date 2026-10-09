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

### Not done / planned (see roadmap at bottom)
- Deployment is **not** done. The owner's chosen path: **VPS + Docker + webhook behind Caddy (HTTPS)**. Verify locally first, then Dockerize, then add domain/HTTPS, then deploy. Keep everything provider-agnostic so other people can self-host too.
- Target timezone for the schedule: **Europe/Berlin** (see gotchas — the code currently uses server-local time).
- `main.py` (FastAPI scaffold) is **deprecated** and slated for deletion — it was only a scratch experiment.
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
| `main.py` | **Deprecated** FastAPI scaffold (scrap). Delete it. |
| `dummy.py` | Scratch script for testing the Groq API directly. Not part of the app. |
| `run_bot.sh` | Bash launcher — **buggy**: references `.venv`, repo uses `venv/`. Fix or replace. |
| `.env.example` | Template for config (copy to `.env`). |

## Running locally

```bash
python -m venv venv
venv\Scripts\activate            # Windows (PowerShell); on Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env             # fill in TELEGRAM_TOKEN and LLM_API_KEY
python bot.py                    # starts in polling mode by default
```

> **Watch out:** the committed `venv/` is currently **stale** — it only has `fastapi`, `uvicorn`, `pydantic` installed. The bot's real deps (`python-telegram-bot`, `openai`, `chromadb`, `fastembed`) are missing; `python bot.py` will fail until `pip install -r requirements.txt` is run.

Environment: Windows dev machine, **Python 3.10** (so the code's `int | None` / `str | None` syntax is fine, but ≥3.10 is required). `requirements.txt` is **unpinned** — pin it before deploying.

## Config (`config.py` / `.env`)

Key vars (full list in `.env.example` / `config.py`): `TELEGRAM_TOKEN`, `LLM_PROVIDER` (groq/openai), `LLM_MODEL` (default `llama-3.1-8b-instant`), `LLM_API_KEY`, `LLM_BASE_URL`, `GERMAN_LEVEL` (A1-A2), `RAG_*`, `EMBEDDING_MODEL`, `SCHEDULE_START_HOUR`/`SCHEDULE_END_HOUR`/`SCHEDULE_MIN/MAX_INTERVAL_MINUTES`, `BOT_MODE` (polling/webhook), `WEBHOOK_URL`/`WEBHOOK_PORT`, `REVIEWER_*`/`CONVERSER_TEMPERATURE`.

## Conventions

- Python 3.10+, plain modules (no package layout), stdlib + the deps in `requirements.txt`.
- Keep code comment-light, match existing style.
- Never commit secrets: `.env`, `chroma_data/`, `chat_id.txt`, `bot.log`, `venv/` are gitignored.
- Preserve provider-agnosticism in any deploy artifacts (Docker, docs) so others can self-host on any VPS/Docker host.
- No test/lint/typecheck setup exists yet — don't invent one without asking the owner first. Run the bot manually to verify behavior (`python bot.py`, then talk to it in Telegram).

## Gotchas / watch-outs

- `memory_store.get_recent_exchanges()` (`memory_store.py`) sorts **after** `collection.get(limit=...)`, so it is **not** actually "most recent" — order is unreliable. Known bug; fix is planned.
- The scheduler's waking-hours check uses server-local `datetime.now()` — deployed timezone must be set (owner wants **Europe/Berlin**), e.g. via `TZ` env / container config. `SCHEDULE_*` currently has no timezone handling.
- `GroqClient` uses OpenAI's newer **`responses` API** (`input=` / `instructions=` kwargs), not `chat.completions`. Only `OpenAIClient` uses `chat.completions`. Don't "fix" one to look like the other unless intentional.
- Default model `llama-3.1-8b-instant` is older; Groq may retire/rename models. If it 404s, update `LLM_MODEL`.
- In-memory conversation history is lost on restart (kept per-process only); ChromaDB persists exchanges across restarts, but RAG is enabled by default while a chat is empty.
- The embedding model is English-focused (`bge-small-en`) but the content is largely German — quality limitation, acceptable for now.
- Webhook mode needs a real HTTPS endpoint (Telegram requires it). The reverse proxy must be added — this is the planned Caddy step.
- Proactive messages use a single `chat_id.txt` (personal-scale feature, one chat at a time).
- Windows dev shell is PowerShell; `run_bot.sh` (bash) is stale/broken as noted.

## Documentation maintenance rules — IMPORTANT

1. **Update this `AGENTS.md` file every time a major feature is added or an important bug is fixed.** Keep status, architecture, config, and gotchas accurate. Don't wait for the owner to ask.
2. **Update `README.md` whenever a MAJOR feature or change is implemented** so the user-facing story stays current. (Minor fixes don't require a README change.)

## Roadmap (incremental)

1. **Verify locally & tidy** — test scheduler end-to-end in polling mode; fix `get_recent_exchanges()` ordering; delete `main.py`; fix/replace `run_bot.sh`; pin `requirements.txt`.
2. **Dockerize** — `Dockerfile`, `docker-compose.yml` (named volume for `chroma_data/`, `chat_id.txt`, logs), `.dockerignore`; env via `.env`/`.env.example`.
3. **Webhook + HTTPS** — Caddy reverse proxy: `Caddy (443 public) → bot container (8443 private)`; `BOT_MODE=webhook`, `WEBHOOK_URL=https://<domain>`, `TZ=Europe/Berlin`; register webhook and verify via `getWebhookInfo`.
4. **Deploy** — provider-agnostic server setup (firewall 22/80/443, SSH keys, clone, `.env`, `docker compose up -d`, logs); full phone-to-bot loop test.
5. **Polish** — README deploy docs, optional Docker healthcheck, future ideas (streak stats, `/stop`-quiet mode, separate stats web app).