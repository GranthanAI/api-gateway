from app.gateway.router import gateway_router

class RoutingService:
    """
    Business service layer encapsulating path routing destination lookup.
    """
    def resolve_route(self, path: str) -> tuple[str, str] | None:
        return gateway_router.route_request(path)

routing_service = RoutingService()
