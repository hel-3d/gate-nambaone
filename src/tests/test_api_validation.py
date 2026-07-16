import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.mark.parametrize(
    "path",
    [
        "/v2/sale_without_card",
        "/v2/status",
        "/v2/refund",
        "/v2/refund_status",
    ],
)
def test_invalid_request_returns_422(
    path: str,
) -> None:
    with TestClient(app) as client:
        response = client.post(
            path,
            json={},
        )

    assert response.status_code == 422

    body = response.json()

    assert body["status"] == "failed"
    assert body["code"] == "validation_error"