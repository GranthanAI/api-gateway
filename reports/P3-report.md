# P3: api-gateway, report

**Commits (local, not pushed):** `e681fa0` P3a: exact public paths, strip trust headers; `d2e7830` P3b: billing routes;
P3c: billing gateway tests and report (the commit that adds this file).  Range: `cfe4bc9..HEAD`.

## What changed
- **P3a.** `app/gateway/paths.py`: `normalize_path` (strip leading `/api/v1`, collapse `//`, strip one trailing `/`, lowercase
  for comparison; `.`/`..` segments, `%2e`, `%2f`, `%5c` and `\` are never public) and `is_public_path` (exact set + `/docs`,
  `/redoc` on a segment boundary). Used by the auth middleware and the OpenAPI aggregator in `main.py`.
  `x-staff-role` and `x-gateway-secret` added to the client-header strip list.
- **P3b.** Settings `BILLING_SERVICE_URL`, `BILLING_GATEWAY_SECRET` (dev default `dev-gateway-secret`, same as billing's),
  `BILLING_SIM_ROUTES`, `DEV_MODE_USERS`; production guard for the secret and the sim flag. `billing` in the registry;
  router mapping (admin and sim before generic; `internal` already blocked by the existing segment check, now also
  `%2e/%2f/%5c`). `app/api/routes/billing.py` (secret, staff role, sim control gate). The JWT `roles` claim is stored on
  `request.state.roles` (missing or malformed = `[]`). `reverse_proxy` takes `extra_headers` and `only_headers`
  (webhook: raw body, only Content-Type / X-Razorpay-Signature / x-razorpay-event-id plus forwarding headers; no cookies, no
  Authorization, no X-User-Id).
- **P3c.** Tests, `.env.example`, README route table, this report.

## Tests run (only these files; full suite not run, owner runs overnight)
| File | Result |
| --- | --- |
| tests/test_public_paths.py | 69 passed |
| tests/test_trust_headers.py | 54 passed |
| tests/test_billing_routes.py | 49 passed |
| tests/test_production_config_guard.py | 7 passed (GOOD config now carries a billing secret) |
| tests/test_file_routing.py | passed (run with the P3b check; part of 151 passed) |
Not run: `tests/test_all_endpoints.py` (needs live services), other existing test files.

## Exit check: NOT run here (billing is not running locally)
Gateway and billing both default to port 8080, so run billing on 8090. Billing repo:
```
PAYMENT_SIMULATION=true GATEWAY_SHARED_SECRET=dev-gateway-secret PORT=8090 \
SIM_WEBHOOK_URL=http://localhost:8080/api/v1/billing/webhooks/razorpay   # then start billing as usual
```
Gateway repo `.env`: `BILLING_SERVICE_URL=http://localhost:8090`, `BILLING_GATEWAY_SECRET=dev-gateway-secret`,
`BILLING_SIM_ROUTES=true`; `make run` (port 8080). Then, with a JWT signed with the gateway's secret (`make token`):
```
cd ../billing-service
BASE_URL=http://localhost:8080 USER_JWT=$(cd ../api-gateway && make -s token) ./scripts/sim_checkout_demo.sh
```
Expect the user on Pro. Then check billing's webhook inbox: the simulator webhooks are processed and there are no
signature failures (`billing_webhook_signature_failed` or equivalent metric stays 0).

## Deviations / decisions
- **Gateway health probes stay public.** The old substring rule made `/auth/health`, `/conversations/health`,
  `/graph/health`, `/llm/health`, `/memory/health` public by accident; they are real routes, so they are in the exact set.
- **`content-encoding` is now dropped from proxied responses** (all services, `response_handler.py`). httpx already decodes the
  body, so keeping the header made clients decode twice. Needed for byte-exact PDFs; affects every service only if one gzips.
- **Sim routes with the flag off:** a request with a valid JWT gets 404; one without gets 401 (authentication runs first). I did
  not make them public-then-404 to avoid widening the auth bypass.
- **Webhook rate limit:** the gateway has no rate limiter, so nothing to exempt. When one is added, exempt
  `POST /billing/webhooks/razorpay`. The 1 MB cap is the existing `MAX_REQUEST_BODY_BYTES` default (exactly 1 MiB passes,
  +1 byte gets 413; tested).
- Sim public checkout accepts only `GET sim/checkout/<id>` and `POST sim/checkout/<id>/pay`; if the simulated page loads other
  assets from `/billing/sim/*` they will need an explicit entry.
- `roles` is read now; until P4 auth-service issues it, `/billing/admin/*` returns 403 as expected.
- Decision for you: should `DEV_MODE_USERS` also be refused in production? It is inert there (sim routes must be off).
