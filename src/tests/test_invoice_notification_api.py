import base64
import hashlib
import hmac
import json
from datetime import UTC
from datetime import datetime

from fastapi.testclient import TestClient

from main import app
from settings import settings

WEBHOOK_PATH = "/notifications/invoice"
MERCHANT_GUID = "159e7e3b-94e1-48c7-bec5-952949f7935f"
WEBHOOK_SECRET = "test-webhook-secret"
SALT = "d5afd864-7559-43d3-9f30-76805f536db9"


def make_payload() -> dict:
    now = datetime.now(UTC).isoformat()

    return {
        "createdAt": now,
        "data": {
            "guid": "payment-guid",
            "externalId": "invoice-1001",
            "channel": "BALANCE",
            "paymentLinkGuid": "payment-link-guid",
            "merchantAccountGuid": MERCHANT_GUID,
            "currency": "KGS",
            "amount": "1050",
            "paymentAmount": "1050",
            "refundAmount": "0",
            "remark": "Test payment",
            "customerGuid": "customer-guid",
            "maskedPhoneNumber": "**********622",
            "status": "COMPLETED",
            "createdAt": now,
            "settledAt": now,
            "type": "PAYMENT_QR",
        },
        "type": "PAYMENT_ORDER",
        "version": "1",
    }


def serialize_payload(payload: dict) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def make_signature(
    body: str,
    *,
    salt: str = SALT,
    secret: str = WEBHOOK_SECRET,
) -> str:
    message = f"{WEBHOOK_PATH}{body}{salt}".encode()

    digest = hmac.new(
        secret.encode(),
        message,
        hashlib.sha512,
    ).digest()

    return base64.b64encode(digest).decode()


def configure_webhook(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "NAMBAONE_BASE_URL",
        "https://provider.example",
    )
    monkeypatch.setattr(
        settings,
        "NAMBAONE_MERCHANT_ID",
        MERCHANT_GUID,
    )
    monkeypatch.setattr(
        settings,
        "NAMBAONE_SECRET",
        WEBHOOK_SECRET,
    )


def test_valid_signed_webhook_returns_200(
    monkeypatch,
) -> None:
    configure_webhook(monkeypatch)

    body = serialize_payload(make_payload())

    headers = {
        "Content-Type": "application/json",
        "x-merchant-api-salt": SALT,
        "x-merchant-api-signature": make_signature(body),
    }

    with TestClient(app) as client:
        response = client.post(
            WEBHOOK_PATH,
            content=body,
            headers=headers,
        )

    assert response.status_code == 200
    assert response.json() == {
        "accepted": True,
        "status": "complete",
        "payment_id": "payment-guid",
        "merchant_payment_id": "invoice-1001",
    }


def test_webhook_without_signature_returns_401(
    monkeypatch,
) -> None:
    configure_webhook(monkeypatch)

    body = serialize_payload(make_payload())

    with TestClient(app) as client:
        response = client.post(
            WEBHOOK_PATH,
            content=body,
            headers={
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "missing_signature"


def test_webhook_with_invalid_signature_returns_401(
    monkeypatch,
) -> None:
    configure_webhook(monkeypatch)

    body = serialize_payload(make_payload())

    with TestClient(app) as client:
        response = client.post(
            WEBHOOK_PATH,
            content=body,
            headers={
                "Content-Type": "application/json",
                "x-merchant-api-salt": SALT,
                "x-merchant-api-signature": "invalid-signature",
            },
        )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_signature"


def test_webhook_with_invalid_json_returns_400(
    monkeypatch,
) -> None:
    configure_webhook(monkeypatch)

    body = "{invalid-json"

    with TestClient(app) as client:
        response = client.post(
            WEBHOOK_PATH,
            content=body,
            headers={
                "Content-Type": "application/json",
                "x-merchant-api-salt": SALT,
                "x-merchant-api-signature": make_signature(body),
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_json"


def test_signed_webhook_with_invalid_schema_returns_422(
    monkeypatch,
) -> None:
    configure_webhook(monkeypatch)

    payload = {
        "type": "PAYMENT_ORDER",
        "version": "1",
        "data": {
            "status": "COMPLETED",
        },
    }
    body = serialize_payload(payload)

    with TestClient(app) as client:
        response = client.post(
            WEBHOOK_PATH,
            content=body,
            headers={
                "Content-Type": "application/json",
                "x-merchant-api-salt": SALT,
                "x-merchant-api-signature": make_signature(body),
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "validation_error"