from decimal import Decimal

import httpx
import pytest
from pytest_httpx import HTTPXMock

from const import PaymentStatus
from gate_nambaone.gate_nambaone import GateNambaOne
from models import RefundStatusRequest

REFUND_STATUS_URL = (
    "https://provider.example"
    "/public/merchant/payment/v1"
    "/159e7e3b-94e1-48c7-bec5-952949f7935f"
    "/refund/refund-1001"
)


def make_request(
    terminal_data: dict,
) -> RefundStatusRequest:
    return RefundStatusRequest(
        refund_id="refund-1001",
        refund_external_id="refund-1001",
        external_id="payment-guid",
        currency_code="KGS",
        terminal_data=terminal_data,
    )


@pytest.mark.asyncio
async def test_refund_status_success(
    gate: GateNambaOne,
    terminal_data: dict,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=REFUND_STATUS_URL,
        json={
            "status": "OK",
            "data": {
                "guid": "provider-refund-guid",
                "currency": "KGS",
                "amount": "500",
                "status": "COMPLETED",
                "externalGuid": "refund-1001",
                "parentPaymentGuid": "payment-guid",
                "errorCode": None,
            },
        },
    )

    response = await gate.refund_status(
        make_request(terminal_data),
    )

    assert response.status == PaymentStatus.COMPLETE
    assert response.amount == Decimal("5.00")
    assert response.refund_external_id == "refund-1001"
    assert response.code is None


@pytest.mark.asyncio
async def test_refund_status_failed_refund(
    gate: GateNambaOne,
    terminal_data: dict,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=REFUND_STATUS_URL,
        json={
            "status": "OK",
            "data": {
                "currency": "KGS",
                "amount": "500",
                "status": "FAILED",
                "externalGuid": "refund-1001",
                "parentPaymentGuid": "payment-guid",
                "errorCode": "02",
            },
        },
    )

    response = await gate.refund_status(
        make_request(terminal_data),
    )

    assert response.status == PaymentStatus.FAILED
    assert response.code == "02"
    assert response.message == "Provider unavailable"


@pytest.mark.asyncio
async def test_refund_status_invalid_terminal_data(
    gate: GateNambaOne,
) -> None:
    request = RefundStatusRequest(
        refund_id="refund-1001",
        currency_code="KGS",
        terminal_data={},
    )

    response = await gate.refund_status(request)

    assert response.status == PaymentStatus.FAILED
    assert response.code == "validation_error"


@pytest.mark.asyncio
async def test_refund_status_invalid_response(
    gate: GateNambaOne,
    terminal_data: dict,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=REFUND_STATUS_URL,
        content=b"invalid-json",
    )

    response = await gate.refund_status(
        make_request(terminal_data),
    )

    assert response.status == PaymentStatus.PENDING
    assert response.code == "invalid_provider_response"


@pytest.mark.asyncio
async def test_refund_status_empty_response(
    gate: GateNambaOne,
    terminal_data: dict,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=REFUND_STATUS_URL,
        content=b"",
    )

    response = await gate.refund_status(
        make_request(terminal_data),
    )

    assert response.status == PaymentStatus.PENDING
    assert response.code == "invalid_provider_response"


@pytest.mark.asyncio
async def test_refund_status_timeout(
    gate: GateNambaOne,
    terminal_data: dict,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_exception(
        httpx.ReadTimeout("Provider timeout"),
    )

    response = await gate.refund_status(
        make_request(terminal_data),
    )

    assert response.status == PaymentStatus.PENDING
    assert response.code == "provider_timeout"