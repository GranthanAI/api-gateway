# Task Update 1: LLM Service Integration & Real-Time SSE Streaming Proxy

This is the first entry in `docs/updates/` for API Gateway, documenting end-to-end validation of every proxied endpoint against the live stack, wiring LLM Service (and Memory Service, for observability) into the gateway, and fixing a real Server-Sent Events streaming gap discovered during that validation.

---

## 1. Executive Summary

The gateway's proxy layer was built for `auth`, `conversation`, and `graph` only. Two gaps were found while validating the full stack end-to-end (all 6 backend services running live, real Kafka round-trips, real Groq generation):

1. **LLM Service had no presence in the gateway at all** — no `LLM_SERVICE_URL` setting, no health-check proxy, no service registry entry. Since LLM Service is Kafka-only for chat (per its HLD, no user-facing HTTP API), the correct addition was a health-check proxy for observability, not a generic reverse-proxy route.
2. **SSE streaming (`GET /stream/{conversation_id}`) was completely unreachable through the gateway** — three independent bugs stacked: no route existed for `/stream/*` at all; the auth middleware only accepted a Bearer header or cookie, not the `?token=` query parameter SSE clients (`EventSource`) actually send; and even with routing fixed, the existing reverse-proxy fully buffers the downstream response (`response.content`) before returning it, so live tokens would only ever arrive all at once after generation finished, not streamed.

All three are fixed and verified live: an SSE connection opened through the gateway now receives the connect ack, heartbeats, and the terminal event as they actually happen.

---

## 2. LLM Service (and Memory Service) Wiring

- `app/core/config.py`: added `LLM_SERVICE_URL` (default `http://localhost:8003`) and `MEMORY_SERVICE_URL` (default `http://localhost:8004`).
- `app/gateway/service_registry.py`: added `"llm"` to the registry map (for consistency with the reverse-proxy pattern, even though LLM Service currently has no proxied routes).
- `app/api/routes/health.py`: added `GET /llm/health` (proxies to LLM Service's `/ready`) and `GET /memory/health` (proxies to Memory Service's `/internal/health/ready` — noted in-code that Memory Service exposes no other public routes, since it's called internally by LLM Service via gRPC, never directly by clients). Both added to the aggregate `/info` endpoint's service-health checks.
- `.env` / `.env.example` updated with both new URLs.

No wildcard reverse-proxy route (`/api/v1/llm/*`) was added — LLM Service has no REST API for chat by design (Kafka-only, per its HLD), so there is nothing to proxy beyond the health check.

---

## 3. SSE Streaming Fix

### 3.1 Missing Route
`app/gateway/router.py`: added a `/stream` → Conversation Service mapping (`/api/v1/stream/{id}` → `/v1/stream/{id}`), alongside a new `app/api/routes/stream.py` route file registered in `main.py`.

### 3.2 Query-Token Auth
`app/middleware/authentication.py`: the middleware previously read only the `Authorization` header or the `access_token` cookie. Browsers' native `EventSource` cannot set custom headers, so Conversation Service's own `get_current_user` dependency already accepted a `?token=` query parameter as a fallback for exactly this reason — the gateway's middleware didn't. Added a scoped exception: for paths starting with `/api/v1/stream/`, fall back to `request.query_params.get("token")` when no header/cookie token is present.

### 3.3 Real Streaming Proxy
The existing `reverse_proxy()` (`app/gateway/proxy.py`) calls `client.request(...)` and returns a fully-materialized `httpx.Response` — correct for every other endpoint, wrong for SSE. Added `reverse_proxy_stream()` alongside it (not a modification to the existing buffered path, since other endpoints don't need streaming): builds the request with `client.build_request()`, sends it with `stream=True`, and — for a `200 OK` upstream response — wraps `upstream_response.aiter_raw()` in a FastAPI `StreamingResponse`, forwarding chunks as they arrive and closing the upstream connection in a `finally` block. Non-200 upstream responses (auth failures, 404s) are read fully and returned through the existing buffered `response_handler.format_response()` path unchanged, since there's nothing to stream in an error case.

`app/api/routes/stream.py` routes exclusively through `reverse_proxy_stream()`.

---

## 4. Verification

### 4.1 Full-Stack Endpoint Sweep
Ran the existing `tests/test_all_endpoints.py` live E2E script (not previously run against a fully live 6-service stack) — all 7 sections passed: gateway health/info, full auth lifecycle (register → verify → login → forgot-password → refresh), user profile, session management, conversations, messages (including regenerate), and graph endpoints. Required adding `asyncpg` to the `dev` dependency group (the script queries the auth database directly to retrieve verification OTPs) and standing up a Postgres container, since none existed anywhere in this project before this session — added to the shared root `docker-compose.yml`.

### 4.2 SSE Live Trace
Opened an SSE connection through the gateway (`GET /api/v1/stream/{id}?token=...`) immediately before sending a message through the same gateway; observed the connect ack (`: ok`), periodic heartbeats, and the terminal `chat.response.generated`-derived event arriving live, in real time, rather than buffered — confirming the fix closes the full loop: gateway → Conversation Service → Redis PubSub → gateway SSE proxy → client.

### 4.3 Cross-Service JWT Trust
Confirmed a JWT minted by Auth Service (`POST /api/v1/auth/login`) is independently verified by the gateway's own middleware, then re-verified and trusted by Conversation Service downstream — the shared `JWT_SECRET_KEY` config is consistent across all three services.

---

## 5. What Was NOT Changed

- The existing buffered `reverse_proxy()` — every non-SSE endpoint (auth, conversations, graph) continues to use it unmodified.
- No changes to Auth Service, Conversation Service, or Graph Service's own APIs — this task only added gateway-side routing, auth, and proxying.

## 6. Known Gaps / Follow-ups

- `embedding-service` (a separate service in this monorepo) is not yet wired into the gateway or `/info` health aggregate — it has no public routes today, matching Memory Service's own internal-only design, so there was nothing to add.
