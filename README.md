# Ek Awaaz

Ek Awaaz is a voice-first emergency coordination demo for the Bolna Symphony Buildathon. A caller speaks naturally in Hindi, Hinglish, Marathi, or English; the system turns the conversation into a structured incident, asks for an explicit confirmation, then coordinates safe, observable response actions.

> **DEMO MODE is on by default.** The bundled simulator never places a real call or sends a real SMS. Real outbound actions require both `DEMO_MODE=false` and `ALLOW_REAL_ACTIONS=true`, explicit caller confirmation, configured providers, and an allowlisted stand-in recipient. Indian emergency numbers are permanently blocked.

## What is included

- Live React operations console with streaming transcript, labeled extraction highlights, incident facts, confidence, correction history, session timer, and action timeline
- FastAPI + WebSocket backend with SQLite event persistence and replay
- Rules-first multilingual extraction with optional Groq structured extraction
- LangGraph dispatcher with explicit confirmation gating, parallel dispatch actions, retries, and a kill switch
- Bolna listener/dispatcher adapter using current v2 agent, call, execution, inbound setup, and webhook flows
- Silent-mode DTMF flow and browser GPS sharing
- Mock-by-default SMS adapter with an opt-in Twilio path
- Searchable reports, incident detail, and downloadable PDF summaries
- Two deterministic demos: spoken road accident with a correction, and silent-mode medical emergency

## Quick start

The pinned runtimes are Python 3.11.9 and Node.js 20.16.0. The demo is safe by
default: it does not place real calls or send real SMS messages.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements.lock

cd frontend
npm ci
npm run build
cd ..

cp .env.example .env
uvicorn backend.main:app --reload
```

Open `http://127.0.0.1:8000`. Choose **Run demo** for the spoken scenario or **Silent demo** for DTMF mode. API docs are at `http://127.0.0.1:8000/docs`.

For separate frontend development:

```bash
cd frontend
npm run dev
```

Vite runs at `http://127.0.0.1:5173` and proxies `/api` and `/ws` to FastAPI on port 8000.

### Docker

Docker is the most reproducible way to run the complete app from a clean Linux
machine. The image builds the frontend and installs the hash-pinned Python
lockfile:

```bash
docker build -t ek-awaaz .
docker run --rm -p 8000:8000 -v "$(pwd)/data:/app/data" ek-awaaz
```

Open `http://127.0.0.1:8000`. To configure providers, pass an environment file
created from `.env.example`:

```bash
docker run --rm --env-file .env -p 8000:8000 -v "$(pwd)/data:/app/data" ek-awaaz
```

## Configuration

Copy `.env.example` to `.env`. The demo works without provider credentials.

| Variable | Purpose |
| --- | --- |
| `DEMO_MODE` | Keeps external actions simulated when `true` |
| `ALLOW_REAL_ACTIONS` | Second, independent switch required for live actions |
| `GROQ_API_KEY` | Enables Groq extraction; rules remain the fallback |
| `BOLNA_API_KEY` | Enables Bolna API requests |
| `BOLNA_LISTENER_AGENT_ID` | Existing inbound listener agent |
| `BOLNA_FROM_PHONE_NUMBER` | Bolna sender number for dispatcher calls |
| `BOLNA_ALLOWED_RECIPIENTS` | Comma-separated stand-in numbers; never real emergency numbers |
| `TWILIO_*` | Optional real SMS configuration |
| `FAMILY_CONTACT_*` | Demo or allowlisted contact details |
| `PUBLIC_BASE_URL` | Public HTTPS URL used by Bolna webhooks |

The full setup checklist is in [docs/bolna-setup.md](docs/bolna-setup.md). The ready-to-paste listener prompt is in [prompts/listener.md](prompts/listener.md).

## Safe live-provider setup

1. Leave `DEMO_MODE=true` while configuring credentials.
2. Create the Bolna listener only through `POST /api/integrations/bolna/create-listener` with `{"confirm": true}`.
3. Configure inbound routing through `POST /api/integrations/bolna/setup-inbound`, also with explicit confirmation.
4. Use only your own verified stand-in numbers in `BOLNA_ALLOWED_RECIPIENTS`.
5. Test the webhook and transcript flow before changing either safety switch.
6. To permit an allowlisted outbound stand-in call, set `DEMO_MODE=false` and `ALLOW_REAL_ACTIONS=true`. Caller confirmation is still mandatory.

The adapter deliberately does not invent a remote “hang up execution” endpoint. **Stop all actions** immediately cancels local simulator/dispatch work and prevents further calls; provider-side termination should only be added against a documented Bolna endpoint.

## Test and build

After installing the pinned dependencies, the single project check is:

```bash
make test
```

This runs the Python test suite and the production frontend build. For a clean
local setup, use `requirements.lock` with `--require-hashes` and `npm ci`:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements.lock
npm --prefix frontend ci
make test
```

The tests cover the full WebSocket simulator path, spoken corrections, protected confirmed fields, the compiled LangGraph dispatcher, PDF generation, and emergency-number blocking.

## System flow

```text
Caller / simulator
       │
       ▼
FastAPI transcript intake ──► rules + optional Groq extraction
       │                              │
       ├──── WebSocket events ◄───────┘
       │
       ▼
Explicit confirmation gate
       │
       ▼
LangGraph dispatcher ──► Bolna stand-in calls / mock-or-Twilio SMS
       │
       ▼
SQLite report + PDF export
```

More detail is in [docs/architecture.md](docs/architecture.md), and the presentation walkthrough is in [docs/demo-script.md](docs/demo-script.md).

## Core API

- `POST /api/sessions` — create a simulator, manual, or Bolna session
- `POST /api/sessions/{id}/simulate?scenario=accident|silent` — run a deterministic demo
- `WS /ws/sessions/{id}` — snapshot plus ordered event stream
- `POST /api/sessions/{id}/transcript` — ingest a caller/agent turn
- `POST /api/sessions/{id}/confirm` — confirm or correct before dispatch
- `POST /api/sessions/{id}/dtmf` — silent-mode confirmation
- `POST /api/sessions/{id}/location` — attach browser GPS
- `POST /api/sessions/{id}/stop` — kill switch
- `GET /api/reports` and `GET /api/reports/{id}/pdf` — report history and PDF export
- `POST /api/webhooks/bolna` — normalized Bolna status/transcript webhook

## Project layout

```text
backend/       FastAPI, orchestration, providers, storage, PDF
frontend/      React/Vite interface
prompts/       Listener and dispatcher scripts
docs/          Architecture, setup, and demo guide
tests/         Integration and safety tests
```
