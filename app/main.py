import httpx
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from app.core.config import settings
from app.core.logging import logger
from app.lifespan import lifespan
from app.core.middleware import register_middleware
from app.api.routes import auth, conversation, graph, health

app = FastAPI(
    title="GraphGPT API Gateway",
    description="Stateless reverse proxy and entry point aggregating all GraphGPT microservices.",
    version="1.0.0",
    lifespan=lifespan,
)

# Register all middlewares (Exception Handler, Logging, Correlation ID, Authentication, CORS)
register_middleware(app)

# Register route controllers (Auth, Conversations, Graph, Health)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(conversation.router, prefix="/api/v1")
app.include_router(graph.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")

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
    )
    
    # Initialize components if not present
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "schemas" not in openapi_schema["components"]:
        openapi_schema["components"]["schemas"] = {}
        
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
                            # Update route tags for clarity in UI
                            for method in path_info.values():
                                if isinstance(method, dict) and "tags" in method:
                                    method["tags"] = [f"{service_name.capitalize()} Service - {t}" for t in method["tags"]]
                                    
                            openapi_schema["paths"][mapped_path] = path_info
                            
                logger.info("Successfully aggregated openapi specs", service=service_name)
            else:
                logger.warning("Service openapi.json returned non-200", service=service_name, status=response.status_code)
        except Exception as e:
            logger.warning("Failed to fetch openapi spec from service", service=service_name, url=openapi_url, error=str(e))

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
