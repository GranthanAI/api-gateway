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

