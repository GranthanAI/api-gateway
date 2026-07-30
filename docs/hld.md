Since you're at the current stage (Auth ✅, Conversation ✅, Graph 🚧), the API Gateway should be **minimal, production-grade, and focused on request routing and authentication**. Don't include features like service discovery, circuit breakers, caching, or rate limiting yet—they can be added later.

---

# API Gateway — High-Level Design (HLD)

# 1. Overview

The API Gateway serves as the **single public entry point** for all client applications interacting with the GraphGPT platform. It acts as a lightweight reverse proxy that authenticates incoming requests, forwards them to the appropriate backend service, and provides common cross-cutting functionality shared across all services.

The Gateway is intentionally designed to remain **stateless** and **business-logic free**. Domain-specific operations are delegated entirely to their respective microservices.

---

# 2. Objectives

The API Gateway is designed to:

* Provide a unified public API endpoint.
* Authenticate incoming requests using JWT access tokens.
* Route requests to backend microservices.
* Propagate user identity and request context.
* Provide centralized CORS handling.
* Standardize API versioning.
* Simplify client interaction by exposing a single endpoint.

---

# 3. Responsibilities

The API Gateway is responsible for:

* Receiving all external HTTP requests.
* Validating JWT access tokens.
* Forwarding authenticated requests to downstream services.
* Injecting authenticated user context into request headers.
* Generating and propagating request tracing metadata.
* Managing CORS policies.
* Routing requests based on URL prefixes.
* Exposing gateway health endpoints.

---

# 4. Non-Responsibilities

The API Gateway does **not**:

* Authenticate users against the database.
* Store business data.
* Execute business logic.
* Access Cassandra or Neo4j directly.
* Consume Kafka events.
* Generate AI responses.
* Perform graph traversals.
* Store conversation or authentication state.

---

# 5. High-Level Architecture

```text
                    Client
                       │
                 HTTPS Request
                       │
                       ▼
                API Gateway
        ┌──────────┼──────────┐
        │          │          │
        ▼          ▼          ▼
  Auth Service  Conversation  Graph Service
```

---

# 6. Request Flow

### Authenticated Request

```text
Client
    │
Bearer Token
    │
    ▼
API Gateway
    │
Validate JWT
    │
Extract User Context
    │
Generate Trace Metadata
    │
Forward Request
    │
Destination Service
    │
Response
    │
Client
```

---

# 7. Routing Responsibilities

| Route Prefix              | Destination Service  |
| ------------------------- | -------------------- |
| `/api/v1/auth/*`          | Auth Service         |
| `/api/v1/conversations/*` | Conversation Service |
| `/api/v1/graph/*`         | Graph Service        |

Future services will be added as new route prefixes without modifying existing clients.

---

# 8. Authentication & Authorization

The Gateway validates every incoming JWT access token before forwarding requests.

After successful validation, the Gateway propagates the authenticated user context to downstream services using internal headers.

Example propagated headers:

```text
X-User-Id
X-Request-Id
X-Trace-Id
X-Correlation-Id
```

Backend services trust only requests originating from the Gateway.

---

# 9. Communication Model

| Source                         | Destination | Protocol |
| ------------------------------ | ----------- | -------- |
| Client → Gateway               | HTTPS       |          |
| Gateway → Auth Service         | HTTP        |          |
| Gateway → Conversation Service | HTTP        |          |
| Gateway → Graph Service        | HTTP        |          |

The Gateway does not communicate with Kafka.

Event-driven communication remains entirely between backend services.

---

# 10. Error Handling

The Gateway standardizes common HTTP responses for:

* Invalid JWT
* Missing authentication
* Invalid routes
* Downstream service unavailable
* Internal gateway failures

Business-specific validation errors remain the responsibility of downstream services.

---

# 11. Security

The Gateway enforces:

* JWT signature verification
* JWT expiration validation
* TLS termination
* Secure header propagation
* CORS policy enforcement

No sensitive credentials are stored within the Gateway.

---

# 12. Data Ownership

The Gateway owns **no persistent business data**.

It only performs transient request processing before forwarding requests to backend services.

---

# 13. Non-Functional Requirements

* Stateless architecture
* Horizontal scalability
* Low request latency
* High availability
* Secure authentication
* Lightweight request routing
* Minimal processing overhead

---

# 14. Service Boundaries

### API Gateway Owns

* Request routing
* JWT validation
* User context propagation
* API version routing
* CORS handling
* Request metadata propagation

### API Gateway Does Not Own

* Authentication business logic
* Conversation lifecycle
* Graph management
* Message persistence
* AI inference
* Event processing
* Database access

---

# 15. Future Scope

The API Gateway is designed to support additional backend services without architectural changes.

Future routing will include:

* LLM Service
* Memory Service
* Retrieval Service
* File Service
* Notification Service
* Search Service
* Analytics Service

Future gateway capabilities may include:

* Rate limiting
* Request throttling
* Response caching
* Circuit breakers
* Load balancing
* Service discovery
* SSE/WebSocket proxy support

---

# 16. Current Scope (v1)

The initial implementation supports:

* JWT authentication
* Request routing
* User context propagation
* Health endpoint
* CORS
* Auth Service routing
* Conversation Service routing
* Graph Service routing

All advanced gateway capabilities are intentionally deferred until additional services are introduced. This keeps the Gateway simple, performant, and aligned with the current stage of the GraphGPT platform.
