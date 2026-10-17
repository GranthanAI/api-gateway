# API Gateway — Endpoint Request Examples

Every endpoint below is what you see in the gateway's Swagger UI at `http://localhost:8080/docs` (aggregated from Auth, Conversation, and Graph Services — LLM and Memory Service expose no public REST API by design, only a health check each). All examples are `curl` against the gateway itself (`http://localhost:8080`), not the downstream services directly.

Endpoints marked **✓ verified live** were actually exercised against the running stack during this session (real Groq generation, real Cassandra/Neo4j/Postgres writes); the rest are schema-accurate but not individually re-run.

Base URL used throughout: `http://localhost:8080`

---

## 1. Gateway Health & Information

### `GET /api/v1/live` — Liveness ✓ verified live
No auth required.
```bash
curl http://localhost:8080/api/v1/live
```
```json
{"status":"UP","message":"Gateway process is alive."}
```

### `GET /api/v1/ready` — Readiness ✓ verified live
```bash
curl http://localhost:8080/api/v1/ready
```
```json
{"status":"UP","details":{"client_pool":"UP"}}
```

### `GET /api/v1/info` — Gateway Info ✓ verified live
Aggregates a health ping to every downstream service.
```bash
curl http://localhost:8080/api/v1/info
```
```json
{"gateway_version":"1.0.0","services":{"auth":"UP","conversation":"UP","llm":"UP","graph":"UP","memory":"UP"}}
```

### `GET /api/v1/auth/health`, `/api/v1/conversations/health`, `/api/v1/graph/health`, `/api/v1/llm/health`, `/api/v1/memory/health` ✓ verified live
Individual proxied health checks, useful when `/info` shows a service `DOWN` and you need the detail.
```bash
curl http://localhost:8080/api/v1/llm/health
```
```json
{"status":"ready","ready":true,"service":"llm-service","version":"2.0.0"}
```
```bash
curl http://localhost:8080/api/v1/memory/health
```
```json
{"status":"ready","checks":{"cassandra":{"status":"ok"},"redis":{"status":"ok"},"milvus":{"status":"ok"},"llm_engine":{"status":"ok"}}}
```

---

## 2. Authentication

None of these require a Bearer token except where noted.

### `POST /api/v1/auth/register` ✓ verified live
```bash
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alex@example.com",
    "password": "SecurePass123!",
    "full_name": "Alex Doe"
  }'
```
`password` must be 12–128 characters.
```json
{
  "id": "b8f7f59c-4e9c-4833-8985-16f34314aea0",
  "email": "alex@example.com",
  "full_name": "Alex Doe",
  "avatar_url": null,
  "is_email_verified": false,
  "status": "PENDING",
  "created_at": "2026-08-30T14:54:04.621971Z",
  "updated_at": "2026-08-30T14:54:04.621971Z",
  "last_login": null
}
```

### `POST /api/v1/auth/resend-verification`
```bash
curl -X POST http://localhost:8080/api/v1/auth/resend-verification \
  -H "Content-Type: application/json" \
  -d '{"email": "alex@example.com"}'
```
```json
{"message": "Verification email sent."}
```

### `POST /api/v1/auth/verify-email` ✓ verified live
`code` is the 6-digit OTP sent to the user's email.
```bash
curl -X POST http://localhost:8080/api/v1/auth/verify-email \
  -H "Content-Type: application/json" \
  -d '{"email": "alex@example.com", "code": "486944"}'
```
```json
{"message": "Email address verified successfully. Your account is now active."}
```

### `POST /api/v1/auth/login` ✓ verified live
Fails with `403` if the account is locked out after repeated failures, or `401` if the email isn't verified yet.
```bash
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alex@example.com", "password": "SecurePass123!"}'
```
```json
{"access_token": "eyJhbGciOiJIUzI1NiIs...", "token_type": "bearer", "expires_in": 900}
```
The gateway also sets an `HttpOnly` `access_token` cookie on this response, so browser clients don't need to store the token themselves. A `refresh_token` cookie is set too, valid 30 days.

### `POST /api/v1/auth/refresh` ✓ verified live
Uses the `refresh_token` cookie automatically — no body needed if the cookie is present.
```bash
curl -X POST http://localhost:8080/api/v1/auth/refresh \
  -H "Cookie: refresh_token=<refresh_token_value>"
```
```json
{"access_token": "eyJhbGciOiJIUzI1NiIs...", "token_type": "bearer", "expires_in": 900}
```

### `POST /api/v1/auth/forgot-password` ✓ verified live
```bash
curl -X POST http://localhost:8080/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "alex@example.com"}'
```
```json
{"message": "If that email exists, a reset link has been sent."}
```

### `POST /api/v1/auth/reset-password`
```bash
curl -X POST http://localhost:8080/api/v1/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{"token": "<reset_token_from_email>", "new_password": "AnotherSecurePass456!"}'
```
```json
{"message": "Password reset successfully."}
```

### `POST /api/v1/auth/logout`
```bash
curl -X POST http://localhost:8080/api/v1/auth/logout \
  -H "Authorization: Bearer <access_token>"
```
Clears the `access_token` cookie on the gateway side as well.

---

## 3. User Profile

All require `Authorization: Bearer <access_token>`.

### `GET /api/v1/auth/me` ✓ verified live
```bash
curl http://localhost:8080/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```
```json
{
  "id": "b8f7f59c-4e9c-4833-8985-16f34314aea0",
  "email": "alex@example.com",
  "full_name": "Alex Doe",
  "avatar_url": null,
  "is_email_verified": true,
  "status": "ACTIVE",
  "created_at": "2026-08-30T14:54:04.621971Z",
  "updated_at": "2026-08-30T14:54:04.621971Z",
  "last_login": "2026-08-30T15:57:15.153810Z"
}
```

### `PATCH /api/v1/auth/profile` ✓ verified live
Both fields optional.
```bash
curl -X PATCH http://localhost:8080/api/v1/auth/profile \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Alexandra Doe"}'
```
```json
{"id": "b8f7f59c-...", "full_name": "Alexandra Doe", "email": "alex@example.com", "...": "..."}
```

### `POST /api/v1/auth/change-password` ✓ verified live
```bash
curl -X POST http://localhost:8080/api/v1/auth/change-password \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"old_password": "SecurePass123!", "new_password": "EvenMoreSecure789!"}'
```
```json
{"message": "Password changed successfully."}
```

---

## 4. Session Management

All require `Authorization: Bearer <access_token>`.

### `GET /api/v1/auth/sessions` ✓ verified live
Lists every device currently logged in.
```bash
curl http://localhost:8080/api/v1/auth/sessions \
  -H "Authorization: Bearer <access_token>"
```
```json
[
  {
    "id": "ae43d4f2-f3e5-4fea-8b43-623dceec8219",
    "device": "Desktop",
    "browser": "Chrome",
    "os": "Windows",
    "ip_address": "127.0.0.1",
    "created_at": "2026-08-30T15:57:15.153810Z",
    "last_seen": "2026-08-30T16:01:00.000000Z",
    "expires_at": "2026-09-29T15:57:15.153810Z"
  }
]
```

### `DELETE /api/v1/auth/sessions/{session_id}` ✓ verified live
Revokes one device session.
```bash
curl -X DELETE http://localhost:8080/api/v1/auth/sessions/ae43d4f2-f3e5-4fea-8b43-623dceec8219 \
  -H "Authorization: Bearer <access_token>"
```
`200 OK`

### `DELETE /api/v1/auth/sessions` ✓ verified live
Revokes every active session for the current user (global logout).
```bash
curl -X DELETE http://localhost:8080/api/v1/auth/sessions \
  -H "Authorization: Bearer <access_token>"
```
`200 OK`

---

## 5. Conversations

All require `Authorization: Bearer <access_token>`.

### `POST /api/v1/conversations` — Create conversation ✓ verified live
`parent_conversation_id` is optional — set it to branch a new conversation off an existing one (see [Section 8](#8-parent--child-conversations)).
```bash
curl -X POST http://localhost:8080/api/v1/conversations \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Kafka deep dive"}'
```
```json
{
  "conversation_id": "01a0532a-6732-7ec6-9ac2-af232bfb05c0",
  "user_id": "b8f7f59c-4e9c-4833-8985-16f34314aea0",
  "title": "Kafka deep dive",
  "created_at": "2026-08-30T14:54:42.994375Z",
  "updated_at": "2026-08-30T14:54:42.994375Z",
  "status": "active",
  "parent_conversation_id": null
}
```

### `GET /api/v1/conversations` — List user conversations ✓ verified live
Cursor-paginated.
```bash
curl "http://localhost:8080/api/v1/conversations?limit=20" \
  -H "Authorization: Bearer <access_token>"
```
```json
{"items": [{"conversation_id": "01a0532a-...", "title": "Kafka deep dive", "status": "active", "...": "..."}], "next_cursor": null, "has_more": false}
```

### `GET /api/v1/conversations/{conversation_id}` — Get conversation ✓ verified live
```bash
curl http://localhost:8080/api/v1/conversations/01a0532a-6732-7ec6-9ac2-af232bfb05c0 \
  -H "Authorization: Bearer <access_token>"
```
`404` if it doesn't exist or belongs to another user, `403` if it exists but isn't yours.

### `PATCH /api/v1/conversations/{conversation_id}/rename` — Rename conversation ✓ verified live
```bash
curl -X PATCH http://localhost:8080/api/v1/conversations/01a0532a-6732-7ec6-9ac2-af232bfb05c0/rename \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Kafka + Groq integration notes"}'
```

### `POST /api/v1/conversations/{conversation_id}/archive` — Archive conversation ✓ verified live
```bash
curl -X POST http://localhost:8080/api/v1/conversations/01a0532a-6732-7ec6-9ac2-af232bfb05c0/archive \
  -H "Authorization: Bearer <access_token>"
```

### `DELETE /api/v1/conversations/{conversation_id}` — Soft delete conversation ✓ verified live
```bash
curl -X DELETE http://localhost:8080/api/v1/conversations/01a0532a-6732-7ec6-9ac2-af232bfb05c0 \
  -H "Authorization: Bearer <access_token>"
```
`204 No Content`

---

## 6. Messages

All require `Authorization: Bearer <access_token>` and conversation ownership.

### `POST /api/v1/conversations/{conversation_id}/messages` — Send user message ✓ verified live
`mode`, `selected_tools`, and `file_ids` are all optional — omit them to reuse whatever the conversation's existing configuration is. `X-Idempotency-Key` (a UUID header) is optional but recommended for safe retries.
```bash
curl -X POST http://localhost:8080/api/v1/conversations/01a0532a-6732-7ec6-9ac2-af232bfb05c0/messages \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: 3f29b1e2-1a4d-4c7a-9e5b-2d6f8a1c9e33" \
  -d '{
    "content": "Explain how Kafka partitions relate to consumer groups.",
    "mode": "default",
    "selected_tools": [],
    "file_ids": []
  }'
```
Returns `202 Accepted` immediately — the actual reply arrives asynchronously via Kafka and is delivered over [SSE](#7-real-time-streaming-sse) or fetched afterward via the history endpoint below.
```json
{
  "message_id": "01a05331-fae8-7941-9720-fe6dbe6b31c9",
  "conversation_id": "01a0532a-6732-7ec6-9ac2-af232bfb05c0",
  "sender": "user",
  "content": "Explain how Kafka partitions relate to consumer groups.",
  "created_at": "2026-08-30T15:02:59.560737Z",
  "status": "sent"
}
```

### `GET /api/v1/conversations/{conversation_id}/messages` — Get conversation message history ✓ verified live
Cursor-paginated, most recent first.
```bash
curl "http://localhost:8080/api/v1/conversations/01a0532a-6732-7ec6-9ac2-af232bfb05c0/messages?limit=50" \
  -H "Authorization: Bearer <access_token>"
```
```json
{
  "items": [
    {
      "message_id": "01a05331-fae8-...",
      "conversation_id": "01a0532a-...",
      "sender": "assistant",
      "content": "Kafka partitions are the unit of parallelism...",
      "created_at": "2026-08-30T15:03:04.000000",
      "status": "sent"
    },
    {
      "message_id": "01a05331-fae8-...",
      "sender": "user",
      "content": "Explain how Kafka partitions relate to consumer groups.",
      "status": "sent"
    }
  ],
  "next_cursor": null,
  "has_more": false
}
```
An assistant message's `status` is `pending` while generation is in flight, `sent` once the real reply lands, or `failed` (with an explanatory `content`, e.g. `"Upstream AI provider error occurred."`) if the LLM Service round-trip errored out.

### `POST /api/v1/conversations/{conversation_id}/messages/{message_id}/regenerate` — Regenerate message ✓ verified live
Re-runs generation for an existing assistant message using the same prompt.
```bash
curl -X POST http://localhost:8080/api/v1/conversations/01a0532a-6732-7ec6-9ac2-af232bfb05c0/messages/01a05331-fae8-7941-9720-fe6dbe6b31c9/regenerate \
  -H "Authorization: Bearer <access_token>"
```
`202 Accepted`, same shape as sending a message.

### `DELETE /api/v1/conversations/{conversation_id}/messages/{message_id}` — Soft delete message ✓ verified live
```bash
curl -X DELETE http://localhost:8080/api/v1/conversations/01a0532a-6732-7ec6-9ac2-af232bfb05c0/messages/01a05331-fae8-7941-9720-fe6dbe6b31c9 \
  -H "Authorization: Bearer <access_token>"
```
`204 No Content`

---

## 7. Real-Time Streaming (SSE)

Not listed in Swagger (registered with `include_in_schema=False` since OpenAPI has no clean way to describe an event stream), but real and gateway-proxied.

### `GET /api/v1/stream/{conversation_id}`  ✓ verified live
Opens a live Server-Sent Events connection carrying `chat.response.chunk` / `chat.response.generated` events as the LLM actually generates them — proxied by the gateway with a genuine streaming reverse-proxy (not buffered), so tokens arrive in real time.

Browsers' native `EventSource` can't set an `Authorization` header, so this endpoint accepts the token as a query parameter instead:
```bash
curl -N "http://localhost:8080/api/v1/stream/01a0532a-6732-7ec6-9ac2-af232bfb05c0?token=<access_token>"
```
```
: ok

: heartbeat

data: {"conversation_id": "01a0532a-...", "message_id": "01a05331-...", "sender": "assistant", "content": "Kafka", "sequence_number": 1, "is_final": false}

data: {"conversation_id": "01a0532a-...", "message_id": "01a05331-...", "sender": "assistant", "content": " partitions", "sequence_number": 2, "is_final": false}

data: {"conversation_id": "01a0532a-...", "message_id": "01a05331-...", "sender": "assistant", "content": "", "is_final": true, "status": "completed"}
```
Typical browser usage:
```javascript
const es = new EventSource(`/api/v1/stream/${conversationId}?token=${accessToken}`);
es.onmessage = (event) => {
  const chunk = JSON.parse(event.data);
  if (chunk.is_final) { es.close(); return; }
  appendToken(chunk.content);
};
```

---

## 8. Parent / Child Conversations

Confirmed live during this session's testing: setting `parent_conversation_id` on `POST /api/v1/conversations` links the two conversations in the graph-lineage sense (visible via the Graph endpoints below) — it does **not** carry the parent's message history or memory into the child. A freshly created child conversation starts with an empty context; only the lineage relationship is inherited.
```bash
curl -X POST http://localhost:8080/api/v1/conversations \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Kafka deep dive — follow-up", "parent_conversation_id": "01a0532a-6732-7ec6-9ac2-af232bfb05c0"}'
```

---

## 9. Graph (Conversation Lineage)

All require `Authorization: Bearer <access_token>`.

### `GET /api/v1/graph/conversations/{conversation_id}` — Get Conversation ✓ verified live
```bash
curl http://localhost:8080/api/v1/graph/conversations/01a0532a-6732-7ec6-9ac2-af232bfb05c0 \
  -H "Authorization: Bearer <access_token>"
```
```json
{"conversation_id": "01a0532a-...", "title": "Kafka deep dive", "user_id": "b8f7f59c-...", "status": "ACTIVE"}
```

### `GET /api/v1/graph/conversations/{conversation_id}/parent` — Get Parent ✓ verified live
```bash
curl http://localhost:8080/api/v1/graph/conversations/01a0532a-6732-7ec6-9ac2-af232bfb05c0/parent \
  -H "Authorization: Bearer <access_token>"
```
`404` if the conversation has no parent (this is the expected, common case).

### `GET /api/v1/graph/conversations/{conversation_id}/children?skip=0&limit=10` — Get Children ✓ verified live
```bash
curl "http://localhost:8080/api/v1/graph/conversations/01a0532a-6732-7ec6-9ac2-af232bfb05c0/children?skip=0&limit=10" \
  -H "Authorization: Bearer <access_token>"
```
```json
[]
```

### `GET /api/v1/graph/conversations/{conversation_id}/ancestors?skip=0&limit=100` — Get Ancestors ✓ verified live
Full root-to-parent lineage chain.
```bash
curl "http://localhost:8080/api/v1/graph/conversations/01a0532a-6732-7ec6-9ac2-af232bfb05c0/ancestors?skip=0&limit=100" \
  -H "Authorization: Bearer <access_token>"
```

### `GET /api/v1/graph/conversations/{conversation_id}/descendants?skip=0&limit=100` — Get Descendants ✓ verified live
Every conversation branched from this one, at any depth.
```bash
curl "http://localhost:8080/api/v1/graph/conversations/01a0532a-6732-7ec6-9ac2-af232bfb05c0/descendants?skip=0&limit=100" \
  -H "Authorization: Bearer <access_token>"
```

---

## 10. Error Shapes

Every gateway/downstream error returns FastAPI's standard shape:
```json
{"detail": "Conversation not found"}
```
or, for request-validation failures (HTTP 422):
```json
{"detail": [{"type": "missing", "loc": ["body", "content"], "msg": "Field required", "input": {}}]}
```

Common status codes across these endpoints: `401` (missing/expired/invalid token), `403` (authenticated but not the resource owner, or account locked out), `404` (resource doesn't exist), `409` (idempotency key already in progress), `422` (request body failed validation), `503` (a downstream service is unreachable — the gateway returns this rather than hanging).

---

## 11. Full Live Walkthrough

This is the exact sequence exercised end-to-end this session, in order — register → verify → login → create conversation → send message → stream the reply → confirm it landed in history:

```bash
BASE=http://localhost:8080/api/v1

# 1. Register
curl -X POST $BASE/auth/register -H "Content-Type: application/json" \
  -d '{"email":"alex@example.com","password":"SecurePass123!","full_name":"Alex Doe"}'

# 2. Verify (use the OTP the account actually received)
curl -X POST $BASE/auth/verify-email -H "Content-Type: application/json" \
  -d '{"email":"alex@example.com","code":"486944"}'

# 3. Login
TOKEN=$(curl -s -X POST $BASE/auth/login -H "Content-Type: application/json" \
  -d '{"email":"alex@example.com","password":"SecurePass123!"}' | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

# 4. Create a conversation
CONV_ID=$(curl -s -X POST $BASE/conversations -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"title":"Kafka deep dive"}' | grep -o '"conversation_id":"[^"]*"' | cut -d'"' -f4)

# 5. Open the SSE stream in the background
curl -N "$BASE/stream/$CONV_ID?token=$TOKEN" &

# 6. Send a message — the SSE connection above starts receiving chunks live
curl -X POST "$BASE/conversations/$CONV_ID/messages" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"content":"Explain how Kafka partitions relate to consumer groups."}'

# 7. Confirm the finished reply is durably stored
curl "$BASE/conversations/$CONV_ID/messages" -H "Authorization: Bearer $TOKEN"
```

---

## Files (via File Service)

All routes require `Authorization: Bearer <access_token>`; the gateway forwards it unchanged. Upload is presign-based: the file bytes go straight from the client to MinIO, never through the gateway. `/internal/**` on File Service is service-to-service only and is never routed (404).

```bash
# 1. Initiate: returns document_id + a presigned PUT URL
curl -X POST http://localhost:8080/api/v1/files/upload/initiate \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"filename":"physics.pdf","content_type":"application/pdf","size_bytes":1024}'

# 2. PUT the bytes to the presigned URL returned above (not via the gateway)
curl -X PUT --upload-file physics.pdf -H "Content-Type: application/pdf" "<upload_url>"

# 3. Complete: triggers ingestion
curl -X POST http://localhost:8080/api/v1/files/$DOC_ID/complete -H "Authorization: Bearer $TOKEN"

# 4. Poll until READY (UPLOADED -> PROCESSING -> READY | FAILED)
curl http://localhost:8080/api/v1/files/$DOC_ID/status -H "Authorization: Bearer $TOKEN"

curl http://localhost:8080/api/v1/files                    -H "Authorization: Bearer $TOKEN"   # list
curl http://localhost:8080/api/v1/files/$DOC_ID            -H "Authorization: Bearer $TOKEN"   # metadata
curl http://localhost:8080/api/v1/files/$DOC_ID/download   -H "Authorization: Bearer $TOKEN"   # presigned GET URL
curl -X POST   http://localhost:8080/api/v1/files/$DOC_ID/retry -H "Authorization: Bearer $TOKEN"  # FAILED -> PROCESSING
curl -X DELETE http://localhost:8080/api/v1/files/$DOC_ID  -H "Authorization: Bearer $TOKEN"
```

Without a token every call returns `401`. See the request body fields in the gateway's Swagger UI (`/docs`, tag **Files**). The exact `initiate` body is defined by File Service's `InitiateUploadRequest`; these examples were not run live.
