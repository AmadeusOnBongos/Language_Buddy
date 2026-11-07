# Language_Buddy — Project Timeline & Plan

Last updated: 2026-11-07
Branch: `main` · Working tree: clean · Last commit: `aff2e2f Cleanup`

This file is the **self-contained project memory**. If you are returning after
months, read this first, then `AGENTS.md` (fast architecture reference) and
`README.md` (user-facing story). It records what the project is, what is done,
what is next, why decisions were made, and what will bite you.

---

## 1. What this project is

A Telegram bot that helps the owner practice German (A1–A2):

1. **Converses** — you write German, the bot replies like a friendly language
   partner. A separate "reviewer" LLM call analyses your message for errors and
   the converser folds corrections into its reply.
2. **Proactively messages** — on a random schedule inside waking hours
   (default 9:00–22:00 Europe/Berlin), it sends a German topic to keep practice
   habitual.
3. **Remembers** — past exchanges are embedded and stored (RAG) so replies can
   reuse context and topics don't repeat.

Built for the Gemma4 hackathon. Secondary purpose: learn LLMs, RAG, and backend
deployment. **The owner wants it built incrementally — do not build the whole
roadmap in one go.**

New planned direction: **analytics on learning progress** (chat logs, time
spent, topic spread, mistakes, nudge effectiveness) via a dashboard.

---

## 2. Where we are right now (snapshot)

- **Phase 0 and Phase 1 are complete and committed.** The bot runs locally in
  polling mode, the scheduler fires, RAG works.
- **Deployment has NOT happened.** No Docker, no domain, no HTTPS, no VPS yet.
- **Analytics has NOT started.** Design is agreed (see §7), nothing implemented.
- **One manual test is still outstanding** — see §9 "Outstanding verification".

---

## 3. Completed work

### Phase 0 — Initial build (earlier sessions)

| Area | Detail |
| --- | --- |
| Bot core (`bot.py`) | `/start` (saves chat_id, clears history), `/bye`, free-text handler |
| Pipeline (`conversation.py`) | reviewer → converser → store; in-memory history (last 20 msgs/chat) |
| LLM clients (`llm_client.py`) | `GroqClient` (default) + `OpenAIClient` behind `LLMClient` ABC |
| RAG (`memory_store.py`) | ChromaDB persistent `./chroma_data/`, FastEmbed `BAAI/bge-small-en-v1.5`, cosine top-k |
| Prompts (`prompts.py`) | reviewer JSON contract, converser persona, topic generator |
| Config (`config.py`) | pydantic-settings from `.env` |
| Scheduler (`scheduler.py`) | `job_queue` random 60–240 min proactive messages, waking-hours gate, self-reschedule |

### Phase 1 — Local verify + tidy (commit `aff2e2f`)

- **Fixed `get_recent_exchanges()` ordering** (`memory_store.py`): was
  `collection.get(limit=N)` then sort → wrong subset. Now fetch all → sort by
  timestamp desc → slice. Correct; acceptable at single-user scale.
- **Added timezone support** (`config.py`, `scheduler.py`): `TIMEZONE` setting
  default `Europe/Berlin`; `ZoneInfo`-based `is_waking_hours()` helper;
  `tzdata` added to requirements (Windows has no system tz database).
- **Deleted `main.py`** — unused FastAPI scaffold.
- **Launchers standardized on `.venv`**:
  - `run_bot.sh` — strict mode, clear error if `.venv` missing, `exec`.
  - `run_bot.ps1` — Windows launcher via `.venv\Scripts\python.exe`.
  - `run_bot.cmd` — double-click trampoline (`-ExecutionPolicy Bypass`, pauses on error).
  - Both machines (Windows + Linux Mint) use `.venv`.
- **`requirements.txt` cleaned + pinned**: removed `fastapi`/`uvicorn`; added
  `tzdata`; pinned `python-dotenv==1.2.4`, `python-telegram-bot[job-queue]==22.8`,
  `openai==3.31.0`, `chromadb==1.5.9`, `fastembed==0.9.0`,
  `pydantic-settings==2.15.0`, `tzdata==2026.5`.
- **Rebuilt local `.venv`** (Python 3.10.0 on Windows) and removed stale `venv/`.
- **Verified**: all modules compile; timezone boundaries (9:00 in / 22:00 out);
  ordering against a real Chroma collection; clean boot twice; scheduler job
  fires at +5s and correctly takes the "no chat_id" path; polling `getUpdates`
  returns 200.
- **Docs**: `AGENTS.md` and `README.md` written/updated.

---

## 4. Decisions log (and why)

| Decision | Choice | Why |
| --- | --- | --- |
| Deploy target | VPS + Docker | Learning backend; cheap; portable |
| Telegram mode | **Webhook** (not polling) | More backend learning; requires HTTPS |
| Reverse proxy | **Caddy** | Automatic HTTPS/cert renewal, tiny config |
| Timezone | `Europe/Berlin` | Owner's wall clock; set `TZ` in container |
| `main.py` | Deleted | Unused scaffold; no FastAPI needed — PTB serves its own webhook |
| Venv folder | `.venv` everywhere | Python default, editor auto-detect, matches Mint laptop |
| Analytics DB | **Postgres** (in docker-compose) | Learning goal; one service added during Dockerize; opens pgvector path |
| Analytics timing | **Capture now, dashboard after deploy** | Start accumulating history; keep deployment as focus |
| Dashboard tech | **Streamlit** | Pure Python, fastest, least frontend work |
| Data split | Postgres = source of truth/analytics; Chroma = vector index | Each tool for its strength; deliberate double-write |

### Why a relational DB for analytics (and not Chroma)

Chroma is a vector store: great at similarity, bad at `GROUP BY`, joins,
aggregations, ordered queries. Recency and analytics belong in SQL. This is the
standard split: **SQL for exact/chronological, vector DB for semantic**, RAG is
the pattern that feeds vector results into the LLM.

### SQLite vs Postgres (the reasoning, kept for later)

- SQLite is objectively sufficient for one user and zero infra; works with the
  double-click launcher.
- Postgres costs one compose service, needs Docker running for local dev, but
  teaches real ops (roles, backups, migrations) and enables `pgvector` later —
  which could replace ChromaDB (and its heavy deps) entirely.
- **Chosen Postgres deliberately, as a learning investment, introduced during
  Dockerization** so it is set up once.

### "Why fetch all" gotcha explained

Chroma `get(limit=N)` has no ordering guarantee, so any correct "most recent"
logic must sort client-side. At ~20 exchanges/day it takes years to reach
100k rows and the fetch is local/file-backed — milliseconds. Do not prematurely
optimize; if it ever slows, scope by `chat_id`, then add a time window, then
split recency into SQL.

---

## 5. Current architecture

| File | Role |
| --- | --- |
| `bot.py` | Entrypoint; handlers, builds manager/store, `setup_scheduler`, polling/webhook |
| `conversation.py` | `process_message` (reviewer→converser→store), `generate_topic`, `clear_history` |
| `scheduler.py` | `chat_id.txt` persistence, `send_proactive_message`, `is_waking_hours`, `schedule_next` |
| `llm_client.py` | `LLMResponse` + `GroqClient`/`OpenAIClient` + `get_llm_client()` |
| `memory_store.py` | Chroma collection, embeddings, similarity, recent, count |
| `prompts.py` | Reviewer/converser/topic prompts + builders |
| `config.py` | `Settings` |
| `run_bot.{sh,ps1,cmd}` | Launchers (`.venv`) |
| `AGENTS.md` / `README.md` | Agent guide / user guide |

Note: `conversation.py:41-45` currently **discards** the reviewer's `errors[]`
array (keeps only `topic` + `has_errors`). This is the key gap for analytics.

---

## 6. Roadmap (canonical)

### Phase 1 — Local verify + tidy ✅ DONE (`aff2e2f`)

### Phase 2 — Postgres + capture + Dockerize ← NEXT

Do capture **before** deploy so history accumulates from day one.

**A. Database foundation + capture**

1. Prerequisite check: Docker Desktop on Windows, `docker compose` on Mint.
2. `docker-compose.yml` — start with `db` service only:
   `postgres:16-alpine`, named volume, creds via `.env`,
   `pg_isready` healthcheck, bind `127.0.0.1:5432` locally.
3. `schema.sql` (applied at startup with `CREATE TABLE IF NOT EXISTS`):
   - `sessions(id, chat_id, started_at, last_activity_at)`
   - `exchanges(id, chat_id, session_id→sessions, user_message, bot_reply,
     topic, has_errors, latency_ms, model, created_at)`
   - `errors(id, exchange_id→exchanges ON DELETE CASCADE, category, severity,
     original, corrected, german_explanation, english_explanation)`
   - `proactive_messages(id, chat_id, topic_text, sent_at, replied_at,
     reply_exchange_id→exchanges)`
   - indexes: `(chat_id, created_at DESC)`, `(exchange_id)`
4. `db.py` — thin `AnalyticsStore` on **psycopg v3** (no ORM). Methods:
   `start_or_touch_session` (gap-based, `SESSION_GAP_MINUTES`, default 15),
   `record_exchange`, `record_proactive`, `mark_proactive_replied`, `close`.
   Sync calls wrapped in `asyncio.to_thread` so handlers stay non-blocking.
5. `prompts.py` — add per-error `category`:
   `articles | verb_conjugation | case | word_order | preposition |
   vocabulary | spelling | other`.
6. `conversation.py` — parse full reviewer JSON incl. `errors`; time both LLM
   calls (`perf_counter`); persist exchange + error rows + session; link reply
   to pending proactive message.
7. `scheduler.py` — insert `proactive_messages` row after each successful send.
8. `config.py` / `.env.example` — `DATABASE_URL`, `SESSION_GAP_MINUTES`;
   extend `LLMResponse` with optional `usage` + `model` (enables token stats).
9. Path refactor — add `DATA_DIR` for `chat_id.txt`, `chroma_data/`, `bot.log`
   so one volume mounts everything.
10. Verify with a throwaway script: insert sample data, run aggregate queries
    (messages/day, streak, session duration, topic spread, error rate by
    severity/category, nudge reply rate), then a live Telegram round-trip.

**B. Dockerize (same block, after A)**

- `Dockerfile` (python:3.10-slim + `libgomp1` for onnxruntime).
- `.dockerignore` (`.venv`, `venv`, `__pycache__`, `.git`, `chroma_data`,
  `*.log`, `.env`, `chat_id.txt`).
- Compose: `bot` service, `depends_on: db (healthy)`, volumes for
  `postgres_data` + `DATA_DIR` + **embedding model cache**,
  `TZ=Europe/Berlin`.
- Verify `docker compose up` boots end-to-end before any VPS exists.

### Phase 3 — Webhook + HTTPS (Caddy)

Topology: `Caddy (443 public) → bot container (8443 private)`.
Set `BOT_MODE=webhook`, `WEBHOOK_URL=https://<domain>`, `TZ=Europe/Berlin`;
register webhook; verify with `getWebhookInfo`.

### Phase 4 — Deploy to VPS

Provider-agnostic steps in the README: firewall 22/80/443, SSH keys, clone,
`.env`, `docker compose up -d`, logs. Full phone→bot loop test.

### Phase 5 — Streamlit dashboard

Separate container, read-only DB connection. Views: activity/streak,
session length, topic spread, error rate by severity/category over time,
proactive nudge effectiveness (sent vs replied, time-to-reply).

### Phase 6 — Polish / future ideas

Deploy docs, optional Docker healthcheck, practice streaks, `/stop` quiet mode,
potential Chroma → pgvector consolidation.

### Reference: cheap hosting options (from earlier research)

| Option | Cost | Notes |
| --- | --- | --- |
| Oracle Cloud Free Tier | $0 | Fiddly signup; instances sometimes reclaimed |
| Hetzner CX23 (2 vCPU/4 GB) | ~€6/mo | EU, good value, Berlin-friendly |
| DigitalOcean Basic (1 GB) | ~$6/mo | Friendliest docs |
| Contabo (4 vCPU/8 GB) | ~$6.25/mo | More RAM, less polished |

Domains: **Cloudflare Registrar** sells at cost (~$10/yr `.com`); budget TLDs
(`.xyz`, `.top`, `.online`) ~$1–3 first year. Realistic floor ~€5–8/mo, or
~€5/yr with Oracle free tier.

---

## 7. Analytics design (agreed, not implemented)

**Capture layer is the real work (~80%); the UI is ~20%.**

- Reviewer output (`errors[]`) is currently thrown away — this is the blocker.
- **"Time spent" is inferred, not measured**: Telegram gives no session events.
  Use a gap heuristic (silence > `SESSION_GAP_MINUTES` starts a new session) and
  report session count/length, active days, streak — not literal wall-clock.
- **Mistake categories** require a reviewer prompt change, not a DB feature.
- **Nudge effectiveness**: log each proactive message and mark it replied when
  the next user message arrives; measures whether the bot's prompting works.
- Postgres for analytics/logs, Chroma stays for similarity. Same content stored
  twice on purpose (different jobs).

---

## 8. Gotchas / watch-outs (consolidated)

**Environment**
- Python **3.10+** required (`int | None` syntax). Windows venv = 3.10.0.
- Both machines use **`.venv`**; `.gitignore` already covers `venv/` and `.venv`.
- `requirements.txt` is **pinned** — keep it that way.
- Windows `zoneinfo` needs **`tzdata`** or `ZoneInfo("Europe/Berlin")` throws.

**Runtime**
- `GroqClient` uses OpenAI's newer **`responses` API** (`input=`/`instructions=`),
  NOT `chat.completions`; `OpenAIClient` uses `chat.completions`. Do not
  accidentally "unify" them.
- Default model `llama-3.1-8b-instant` is old; Groq may retire it — if 404,
  update `LLM_MODEL`.
- In-memory history dies on restart (by design); Chroma persists.
- Embedding model is **English-focused** (`bge-small-en`) for German content —
  known quality limitation.
- `chat_id.txt` supports a **single chat only** (personal-scale by design).

**Analytics / Postgres (upcoming)**
- **Local dev will require Postgres running** (`docker compose up -d db`);
  the double-click launcher no longer works alone.
- **FastEmbed downloads ~80 MB on first run** — in Docker, use a cache volume
  or bake it in, else every rebuild re-downloads.
- **onnxruntime needs `libgomp1`** on slim images; Chroma pulls heavy deps
  (image likely 1 GB+).
- No Alembic yet — schema changes are manual until migrations are justified.
- Reviewer prompt change affects parsing — tolerate a missing `category`.
- `LLMResponse` has no `usage`/model today; extend it if you want token/cost
  stats.

**Security / logs**
- `httpx` logs full Telegram URLs **including the bot token** into `bot.log`
  (gitignored). Never paste log excerpts publicly without redacting. Rotate via
  `@BotFather /revoke` if exposed.
- Never commit `.env`, `chroma_data/`, `chat_id.txt`, `bot.log`, `.venv/`.

**Verification**
- There is **no test/lint/typecheck setup**. Per `AGENTS.md`, do not invent one
  without asking the owner. Verify by running the bot manually and with
  throwaway scripts.

---

## 9. Outstanding verification (do this first when you return)

- [ ] Real phone test: double-click `run_bot.cmd` (with `.venv` + `.env`), send
      `/start`, chat a few German sentences → confirm real LLM replies and
      corrections.
- [ ] Confirm a **proactive topic is actually delivered** after `/start`
      (Phase 1 only verified the "no chat_id" skip path in logs).
- [ ] If anything misbehaves, check `bot.log` tail and reply quality.

---

## 10. How to resume

```powershell
# Windows
docker compose up -d db        # once Phase 2 exists
.\.venv\Scripts\Activate.ps1   # or just double-click run_bot.cmd
python bot.py
```

```bash
# Linux Mint
docker compose up -d db        # once Phase 2 exists
source .venv/bin/activate
python bot.py
```

Then: do §9, confirm Docker is installed, and start **Phase 2A** (schema +
`db.py` + capture), before writing any Docker files.

**Defaults already chosen** (unless the owner changes them): psycopg v3 sync +
`asyncio.to_thread`; no ORM; no Alembic yet; do the `DATA_DIR` refactor now;
keep `chat_id.txt` for now (remove later); Streamlit for the dashboard.

---

## 11. Documentation rules (from `AGENTS.md`)

1. Update **`AGENTS.md`** on every major feature or important bug fix.
2. Update **`README.md`** on every MAJOR feature/change.
3. Keep **this file** current too: update the snapshot (§2), completed work
   (§3), and status of the roadmap (§6) whenever a phase advances.
