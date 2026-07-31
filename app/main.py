import httpx
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from app.core.config import settings
from app.core.logging import logger
from app.lifespan import lifespan
from app.core.middleware import register_middleware
from app.api.routes import auth, conversation, graph, health, users, sessions

tags_metadata = [
    {"name": "Gateway Health & Information", "description": "Liveness, readiness, and service statuses"},
    {"name": "Authentication", "description": "User registration, login, token refresh, and verification flow"},
    {"name": "User Profile", "description": "Manage profile information and credentials"},
    {"name": "Session Management", "description": "Active session tracking and device revocation"},
    {"name": "Conversations", "description": "Manage conversation catalogs and branching"},
    {"name": "Messages", "description": "Send and retrieve messages, streaming history, and regeneration"},
    {"name": "Graph", "description": "Asynchronous Neo4j lineage visualization and search operations"},
]

app = FastAPI(
    title="GraphGPT API Gateway",
    description="Stateless reverse proxy and entry point aggregating all GraphGPT microservices.",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
)

# Register all middlewares (Exception Handler, Logging, Correlation ID, Authentication, CORS)
register_middleware(app)

# Register route controllers (Health must be registered first to override catch-all proxy wildcards)
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(conversation.router, prefix="/api/v1")
app.include_router(graph.router, prefix="/api/v1")


# --- Dynamic OpenAPI Schema Aggregator ---

def custom_openapi():
    """
    Dynamically fetches and aggregates the OpenAPI JSON specifications from
    downstream microservices (Auth, Conversation, Graph) to build a unified
    Swagger UI playground on the Gateway.
    """
    if app.openapi_schema:
        return app.openapi_schema

    # Generate gateway base schema (only contains /live and /ready)
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    
    # Initialize components if not present
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "schemas" not in openapi_schema["components"]:
        openapi_schema["components"]["schemas"] = {}
        
    # Inject global BearerAuth security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your Bearer access_token to access protected endpoints."
        }
    }
        
    client = httpx.Client(timeout=5.0)

    # Downstream OpenAPIs mapping
    services_to_fetch = [
        ("auth", settings.AUTH_SERVICE_URL, "/api/v1/auth"),
        ("conversation", settings.CONVERSATION_SERVICE_URL, "/api/v1/conversations"),
        ("graph", settings.GRAPH_SERVICE_URL, "/api/v1/graph")
    ]

    for service_name, base_url, gateway_prefix in services_to_fetch:
        openapi_url = f"{base_url.rstrip('/')}/openapi.json"
        try:
            response = client.get(openapi_url)
            if response.status_code == 200:
                service_schema = response.json()
                
                # Merge Schemas
                if "components" in service_schema and "schemas" in service_schema["components"]:
                    for schema_name, schema_val in service_schema["components"]["schemas"].items():
                        openapi_schema["components"]["schemas"][schema_name] = schema_val
                
                # Merge Paths
                if "paths" in service_schema:
                    for path, path_info in service_schema["paths"].items():
                        mapped_path = None
                        if service_name == "auth":
                            if path.startswith("/auth"):
                                mapped_path = "/api/v1" + path
                            elif path.startswith("/users"):
                                mapped_path = "/api/v1" + path
                            elif path.startswith("/sessions"):
                                mapped_path = "/api/v1" + path
                        elif service_name == "conversation":
                            if path.startswith("/v1/conversations"):
                                mapped_path = "/api/v1/conversations" + path[len("/v1/conversations"):]
                        elif service_name == "graph":
                            if path.startswith("/graph"):
                                mapped_path = "/api/v1/graph" + path[len("/graph"):]
                                
                        if mapped_path:
                            # Map to the precise User Journey tag
                            journey_tag = "Authentication"
                            if service_name == "graph":
                                journey_tag = "Graph"
                            elif service_name == "conversation":
                                if "/messages" in mapped_path:
                                    journey_tag = "Messages"
                                else:
                                    journey_tag = "Conversations"
                            elif service_name == "auth":
                                if "/sessions" in mapped_path:
                                    journey_tag = "Session Management"
                                elif any(p in mapped_path for p in ["/me", "/profile", "/change-password"]):
                                    journey_tag = "User Profile"
                                else:
                                    journey_tag = "Authentication"

                            # Check if the endpoint requires auth (is NOT public)
                            is_public = False
                            path_suffix = mapped_path
                            if path_suffix.startswith("/api/v1"):
                                path_suffix = path_suffix[len("/api/v1"):]
                            
                            from app.middleware.authentication import PUBLIC_PATHS
                            if any(p in path_suffix for p in PUBLIC_PATHS):
                                is_public = True

                            # Update route tags and inject security requirement
                            for method in path_info.values():
                                if isinstance(method, dict):
                                    if "tags" in method:
                                        method["tags"] = [journey_tag]
                                    if not is_public:
                                        method["security"] = [{"BearerAuth": []}]
                                    
                            openapi_schema["paths"][mapped_path] = path_info
                            
                logger.info("Successfully aggregated openapi specs", service=service_name)
            else:
                logger.warning("Service openapi.json returned non-200", service=service_name, status=response.status_code)
        except Exception as e:
            logger.warning("Failed to fetch openapi spec from service", service=service_name, url=openapi_url, error=str(e))

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
