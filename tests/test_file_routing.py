import pytest

from app.gateway.router import gateway_router


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/files",
        "/api/v1/files/upload/initiate",
        "/api/v1/files/0190a1b2-0000-7000-8000-000000000001/status",
    ],
)
def test_file_paths_route_to_file_service_unchanged(path):
    service, target = gateway_router.route_request(path)
    assert service == "file"
    assert target == path[len("/api/v1"):]


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/internal/files/permissions/check",
        "/api/v1/files/internal/files/permissions/check",
        "/api/v1/files/../internal/files/permissions/check",
        "/api/v1/files/Internal/x",
        "/api/v1/files/./x",
    ],
)
def test_internal_and_traversal_paths_are_not_routed(path):
    assert gateway_router.route_request(path) is None


def test_files_prefix_does_not_swallow_lookalikes():
    assert gateway_router.route_request("/api/v1/filesystem") is None



def test_client_supplied_identity_header_is_never_forwarded():
    from app.gateway.request_forwarder import HOP_BY_HOP_HEADERS

    assert "x-user-id" in HOP_BY_HOP_HEADERS


def test_preferences_route_to_conversation_service():
    assert gateway_router.route_request("/api/v1/preferences") == ("conversation", "/v1/preferences")


@pytest.mark.parametrize("path", ["/api/v1/memory/settings", "/api/v1/memory/facts",
                                  "/api/v1/memory/facts/0190a1b2-0000-7000-8000-000000000001"])
def test_user_memory_routes_go_to_memory_service_unchanged(path):
    assert gateway_router.route_request(path) == ("memory", path[len("/api/v1"):])


@pytest.mark.parametrize("path", ["/api/v1/memory/internal/memory/context", "/api/v1/memory/llm/summarize",
                                  "/api/v1/memory/context", "/api/v1/memory"])
def test_other_memory_paths_are_not_routed(path):
    assert gateway_router.route_request(path) is None


def test_memory_and_preferences_require_auth():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    assert client.get("/api/v1/preferences").status_code == 401
    assert client.get("/api/v1/memory/facts").status_code == 401


def test_custom_modes_route_to_conversation_service():
    assert gateway_router.route_request("/api/v1/custom-modes") == ("conversation", "/v1/custom-modes")
    mode = "3f2c1c2e-0000-4000-8000-000000000001"
    assert gateway_router.route_request(f"/api/v1/custom-modes/{mode}") == ("conversation", f"/v1/custom-modes/{mode}")


def test_custom_modes_require_auth_and_only_allowed_methods_are_routed():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    assert client.get("/api/v1/custom-modes").status_code == 401
    assert client.post("/api/v1/custom-modes", json={}).status_code == 401
    assert client.delete("/api/v1/custom-modes/x").status_code == 401
