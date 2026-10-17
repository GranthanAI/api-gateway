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

        # Never forward traversal segments or anything under an "internal"
        # segment: file-service's /internal/** is service-to-service only, and
        # the HTTP client normalizes ".." so "/files/../internal/..." would
        # otherwise land on it.
        segments = [s.lower() for s in normalized_path.split("/")]
        if any(s in ("..", ".", "internal") for s in segments):
            return None

        if normalized_path.startswith("/auth"):
            return "auth", "/auth" + normalized_path[len("/auth"):]
        elif normalized_path.startswith("/users"):
            return "auth", "/users" + normalized_path[len("/users"):]
        elif normalized_path.startswith("/sessions"):
            return "auth", "/sessions" + normalized_path[len("/sessions"):]
        elif normalized_path.startswith("/conversations"):
            return "conversation", "/v1/conversations" + normalized_path[len("/conversations"):]
        elif normalized_path.startswith("/stream"):
            return "conversation", "/v1/stream" + normalized_path[len("/stream"):]
        elif normalized_path == "/files" or normalized_path.startswith("/files/"):
            return "file", normalized_path
        elif normalized_path.startswith("/graph"):
            return "graph", "/graph" + normalized_path[len("/graph"):]
            
        return None

gateway_router = GatewayRouter()
