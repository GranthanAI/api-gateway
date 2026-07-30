# GraphGPT API Gateway

The **API Gateway** serves as the single public entry point for all client applications interacting with the GraphGPT platform. It acts as a lightweight, stateless reverse proxy that validates JWT access tokens, injects correlation context, and forwards traffic downstream to appropriate microservices.

---

## Architecture Overview

```text
                           Client
                              │
                        HTTP Request
                              │
                              ▼
                         API Gateway (Port 8080)
                              ├─ Decodes & Validates JWT (Shared Secret)
                              ├─ Generates/Propagates X-Correlation-ID
                              └─ Resolves Routing Target URL
                                    │
           ┌────────────────────────┼────────────────────────┐
           ▼                        ▼                        ▼
     Auth Service         Conversation Service         Graph Service
     (Port 8001)              (Port 8002)              (Port 8000)
```

### Routing Mappings

| Inbound Gateway URL | Stripped Route Prefix | Target Service Base URL | Target Downstream Route |
| :--- | :--- | :--- | :--- |
| `/api/v1/auth/*` | `/api/v1/auth` | `AUTH_SERVICE_URL` | `/auth/*` |
| `/api/v1/users/*` | `/api/v1/users` | `AUTH_SERVICE_URL` | `/users/*` |
| `/api/v1/sessions/*` | `/api/v1/sessions` | `AUTH_SERVICE_URL` | `/sessions/*` |
| `/api/v1/conversations/*` | `/api/v1/conversations` | `CONVERSATION_SERVICE_URL` | `/v1/conversations/*` |
| `/api/v1/graph/*` | `/api/v1/graph` | `GRAPH_SERVICE_URL` | `/graph/*` |

---

## Port Allocations (Local Development)

To run the entire suite locally without conflicts, configure the target ports in `.env` files matching the mapping below:

* **Graph Service**: Port `8000` (Neo4j on `7687`)
* **Auth Service**: Port `8001` (PostgreSQL on `5432`, Redis on `6379`)
* **Conversation Service**: Port `8002` (Cassandra on `9042`, Kafka on `9092`)
* **API Gateway**: Port `8080`

---

## How to Start All Services Locally

### Step 1: Start Databases & Brokers (Docker Containers)

Launch local Cassandra, Neo4j, Redis, PostgreSQL, and Kafka containers:

1. **Auth Service Databases** (PostgreSQL & Redis):
   ```bash
   cd auth-service
   docker compose up -d
   ```
2. **Conversation Service Infrastructure** (Cassandra, Redis, Kafka):
   ```bash
   cd conversation-service
   docker compose up -d
   ```
3. **Graph Service Database** (Neo4j):
   ```bash
   cd graph-service
   make docker-up
   ```

Wait for all databases to pass their respective readiness health probes.

---

### Step 2: Initialize Database Schemas

Before running the microservices, apply CQL/SQL schemas:

1. **Auth Service Tables Setup**:
   ```bash
   cd auth-service
   make sync
   make init-db
   ```
2. **Conversation Service Cassandra Schema**:
   ```bash
   cd conversation-service
   make setup
   make schema
   ```

---

### Step 3: Start the Backend Microservices

Launch the microservice application servers in separate terminal panes:

1. **Start Graph Service** (Port `8000`):
   ```bash
   cd graph-service
   make run
   ```
2. **Start Auth Service** (Port `8001`):
   Edit the Makefile or uvicorn command command line to specify port `8001`:
   ```bash
   cd auth-service
   uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
   ```
3. **Start Conversation Service** (Port `8002`):
   Run uvicorn with port `8002`:
   ```bash
   cd conversation-service
   uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8002
   ```

---

### Step 4: Start the API Gateway (Port `8080`)

Once downstream microservices are running, launch the Gateway:

```bash
cd api-gateway
make install
make run
```

---

## 🔍 How to Test All Endpoints in One Interface

The API Gateway is configured with a **dynamic OpenAPI aggregator**. 

Open your browser and navigate to:
👉 **`http://localhost:8080/docs`**

The Gateway automatically polls the `/openapi.json` specs from the Auth, Conversation, and Graph services, translates their routes, and exposes them in a **single Swagger UI playground**.

### Manual Test Steps in Swagger:

1. **Register & Login (Public)**:
   - Expand the **`Auth Service`** endpoints.
   - Use `/api/v1/auth/register` to register a new user profile.
   - Call `/api/v1/auth/login` to obtain an access JWT token.
   - Copy the `access_token` string from the JSON response.

2. **Authorize Swagger**:
   - Scroll to the top of the Swagger page and click the green **Authorize** button.
   - Enter your token: `Bearer <paste_your_jwt_here>`.
   - Click **Authorize** and close the dialog.

3. **Call Protected Endpoints**:
   - All subsequent requests (like creating a conversation under **`Conversation Service`** or retrieving nodes from **`Graph Service`**) will automatically include your Bearer token in the `Authorization` header.
   - The Gateway validates the JWT, injects `X-User-Id` downstream, propagates the request context with an `X-Correlation-ID` header, and reverse proxies the call.
