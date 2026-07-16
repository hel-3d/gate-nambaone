from decimal import Decimal

import httpx
import pytest
from pytest_httpx import HTTPXMock

from const import PaymentStatus
from gate_nambaone.gate_nambaone import GateNambaOne
from models import RefundRequest

REFUND_URL = (
    "https://provider.example"
    "/public/merchant/payment/v1"
    "/159e7e3b-94e1-48c7-bec5-952949f7935f"
    "/refund/refund-1001"
)


def make_request(
    terminal_data: dict,
) -> RefundRequest:
    return RefundRequest(
        refund_id="refund-1001",
        invoice_id="invoice-1001",
        external_id=(
            "b9433c7e-ad39-4a08-8346-6beec796d20d"
        ),
        amount=Decimal("5.00"),
        currency_code="KGS",
        reason="Customer returned the product",
        terminal_data=terminal_data,
    )


@pytest.mark.asyncio
async def test_refund_success(
    gate: GateNambaOne,
    terminal_data: dict,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=REFUND_URL,
        json={
            "status": "OK",
            "data": {
                "guid": (
                    "8635e567-544d-4a98-ba9b-e741085e1cee"
                ),
                "currency": "KGS",
                "amount": "500",
                "status": "CREATED",
                "externalGuid": "refund-1001",
                "parentPaymentGuid": (
                    "b9433c7e-ad39-4a08-8346-6beec796d20d"
                ),
            },
        },
    )

    response = await gate.refund(
        make_request(terminal_data),
    )

    assert response.status == PaymentStatus.PENDING
    assert response.amount == Decimal("5.00")
    assert response.refund_external_id == "refund-1001"


@pytest.mark.asyncio
async def test_refund_provider_rejection(
    gate: GateNambaOne,
    terminal_data: dict,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=REFUND_URL,
        json={
            "status": "ERROR",
            "data": None,
            "error": {
                "errorCode": "REFUND_PARENT_ORDER_WRONG_STATUS",
                "message": "Parent payment order wrong status",
            },
        },
    )

    response = await gate.refund(
        make_request(terminal_data),
    )

    assert response.status == PaymentStatus.FAILED
    assert response.code == "REFUND_PARENT_ORDER_WRONG_STATUS"


@pytest.mark.asyncio
async def test_refund_invalid_terminal_data(
    gate: GateNambaOne,
) -> None:
    request = RefundRequest(
        refund_id="refund-1001",
        invoice_id="invoice-1001",
        external_id="payment-guid",
        amount=Decimal("5.00"),
        currency_code="KGS",
        terminal_data={},
    )

    response = await gate.refund(request)

    assert response.status == PaymentStatus.FAILED
    assert response.code == "validation_error"


@pytest.mark.asyncio
async def test_refund_invalid_provider_json(
    gate: GateNambaOne,
    terminal_data: dict,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=REFUND_URL,
        content=b"invalid-json",
    )

    response = await gate.refund(
        make_request(terminal_data),
    )

    assert response.status == PaymentStatus.FAILED
    assert response.code == "invalid_provider_response"


@pytest.mark.asyncio
async def test_refund_empty_provider_response(
    gate: GateNambaOne,
    terminal_data: dict,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=REFUND_URL,
        content=b"",
    )

    response = await gate.refund(
        make_request(terminal_data),
    )

    assert response.status == PaymentStatus.FAILED
    assert response.code == "invalid_provider_response"


@pytest.mark.asyncio
async def test_refund_timeout(
    gate: GateNambaOne,
    terminal_data: dict,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_exception(
        httpx.ReadTimeout("Provider timeout"),
    )

    response = await gate.refund(
        make_request(terminal_data),
    )

    assert response.status == PaymentStatus.FAILED
    assert response.code == "provider_timeout"