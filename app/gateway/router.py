from app.gateway.service_registry import service_registry

class GatewayRouter:
    """
    Decides routing destinations for incoming gateway request paths.
    """
    def route_request(self, path: str) -> tuple[str, str] | None:
        """
        Routes the incoming path to (service_name, target_path_suffix).
        Normalizes api prefixes (like /api/v1/auth -> /auth downstream).
        """
        normalized_path = path
        if path.startswith("/api/v1"):
            normalized_path = path[len("/api/v1"):]

        if normalized_path.startswith("/auth"):
            return "auth", "/auth" + normalized_path[len("/auth"):]
        elif normalized_path.startswith("/users"):
            return "auth", "/users" + normalized_path[len("/users"):]
        elif normalized_path.startswith("/sessions"):
            return "auth", "/sessions" + normalized_path[len("/sessions"):]
        elif normalized_path.startswith("/conversations"):
            return "conversation", "/v1/conversations" + normalized_path[len("/conversations"):]
        elif normalized_path.startswith("/graph"):
            return "graph", "/graph" + normalized_path[len("/graph"):]
            
        return None

gateway_router = GatewayRouter()
