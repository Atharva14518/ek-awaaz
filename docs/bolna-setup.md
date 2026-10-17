# Bolna setup

The current documented contracts are isolated in `backend/bolna_client.py`:

- `POST /v2/agent` creates an agent and returns HTTP 201.
- `POST /call` starts an outbound call and returns an `execution_id`.
- `GET /executions/{id}` retrieves call state.
- `POST /inbound/setup` links an agent and phone number.
- Agent webhooks deliver execution updates through `POST /api/webhooks/bolna`.

Official references: [API introduction](https://www.bolna.ai/docs/api-reference/introduction), [webhooks](https://www.bolna.ai/docs/post-call/polling-call-status-webhooks), and [API quickstart](https://www.bolna.ai/docs/quickstarts/api).

## Safe configuration

1. Copy `.env.example` to `.env`.
2. Add `BOLNA_API_KEY`, a public `PUBLIC_BASE_URL`, and a random `BOLNA_WEBHOOK_SECRET`.
3. Configure three numbers you own as `AMBULANCE_DEMO_NUMBER`, `POLICE_DEMO_NUMBER`, and `FAMILY_DEMO_NUMBER`.
4. Create or configure the Listener with `prompts/listener.md`.
5. Add `https://your-host/api/webhooks/bolna` in the agent Extractions tab. Add the `X-Ek-Awaaz-Secret` header if supported.
6. Set the agent ID and Bolna phone-number ID, then explicitly call `/api/integrations/bolna/setup-inbound` with `{ "confirm": true }`.
7. Leave `DEMO_MODE=true` and `ALLOW_REAL_ACTIONS=false` until every recipient is a verified stand-in.
8. Enable stand-in actions only by setting `DEMO_MODE=false` and `ALLOW_REAL_ACTIONS=true` together.

## Live transcript bridge

The normal execution webhook can contain transcript data and is normalized by the app. For sub-call live chunks, configure a Bolna custom function or streaming bridge to send:

```json
POST /api/sessions/{session_id}/transcript
{
  "speaker": "caller",
  "text": "Bike accident near the blue temple",
  "source": "bolna"
}
```

The simulator uses this same orchestration path.

## Kill-switch limitation

Bolna's public documentation does not document a single-execution stop endpoint. The visible kill switch stops pending local actions and prevents new calls. Add provider-side termination only when Bolna documents a supported endpoint; the adapter intentionally does not guess one.

