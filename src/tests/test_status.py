from decimal import Decimal

import httpx
import pytest
from pytest_httpx import HTTPXMock

from const import PaymentStatus
from gate_nambaone.gate_nambaone import GateNambaOne
from models import StatusRequest

STATUS_URL = (
    "https://provider.example"
    "/public/merchant/payment/v1"
    "/159e7e3b-94e1-48c7-bec5-952949f7935f"
    "/one-time/invoice-1001"
)


def make_request(
    terminal_data: dict,
) -> StatusRequest:
    return StatusRequest(
        invoice_id="invoice-1001",
        external_id="invoice-1001",
        currency_code="KGS",
        terminal_data=terminal_data,
    )


@pytest.mark.asyncio
async def test_status_success(
    gate: GateNambaOne,
    terminal_data: dict,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=STATUS_URL,
        json={
            "status": "OK",
            "data": {
                "guid": (
                    "def45632-9604-4a4e-9890-65b03662d29b"
                ),
                "currency": "KGS",
                "amount": "1050",
                "paymentAmount": "1050",
                "refundAmount": "0",
                "status": "COMPLETED",
            },
        },
    )

    response = await gate.status(
        make_request(terminal_data),
    )

    assert response.status == PaymentStatus.COMPLETE
    assert response.amount == Decimal("10.50")
    assert response.currency_code == "KGS"
    assert response.external_id == (
        "def45632-9604-4a4e-9890-65b03662d29b"
    )


@pytest.mark.asyncio
async def test_status_empty_data_means_pending(
    gate: GateNambaOne,
    terminal_data: dict,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=STATUS_URL,
        json={
            "status": "OK",
        },
    )

    response = await gate.status(
        make_request(terminal_data),
    )

    assert response.status == PaymentStatus.PENDING
    assert response.amount is None
    assert response.external_id == "invoice-1001"


@pytest.mark.asyncio
async def test_status_provider_error(
    gate: GateNambaOne,
    terminal_data: dict,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=STATUS_URL,
        json={
            "status": "ERROR",
            "error": {
                "errorCode": "PAYMENT_ORDER_NOT_FOUND_EXCEPTION",
                "message": "Payment order not found",
            },
        },
    )

    response = await gate.status(
        make_request(terminal_data),
    )

    assert response.status == PaymentStatus.PENDING
    assert response.code == "PAYMENT_ORDER_NOT_FOUND_EXCEPTION"
    assert response.message == "Payment order not found"


@pytest.mark.asyncio
async def test_status_invalid_terminal_data(
    gate: GateNambaOne,
) -> None:
    request = StatusRequest(
        invoice_id="invoice-1001",
        currency_code="KGS",
        terminal_data={},
    )

    response = await gate.status(request)

    assert response.status == PaymentStatus.FAILED
    assert response.code == "validation_error"


@pytest.mark.asyncio
async def test_status_invalid_provider_response(
    gate: GateNambaOne,
    terminal_data: dict,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=STATUS_URL,
        content=b"<html>unexpected response</html>",
    )

    response = await gate.status(
        make_request(terminal_data),
    )

    assert response.status == PaymentStatus.PENDING
    assert response.code == "invalid_provider_response"


@pytest.mark.asyncio
async def test_status_empty_http_response(
    gate: GateNambaOne,
    terminal_data: dict,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=STATUS_URL,
        content=b"",
    )

    response = await gate.status(
        make_request(terminal_data),
    )

    assert response.status == PaymentStatus.PENDING
    assert response.code == "invalid_provider_response"


@pytest.mark.asyncio
async def test_status_timeout(
    gate: GateNambaOne,
    terminal_data: dict,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_exception(
        httpx.ReadTimeout("Provider timeout"),
    )

    response = await gate.status(
        make_request(terminal_data),
    )

    assert response.status == PaymentStatus.PENDING
    assert response.code == "provider_timeout"