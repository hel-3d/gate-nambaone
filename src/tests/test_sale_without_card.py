from decimal import Decimal

import httpx
import pytest
from pytest_httpx import HTTPXMock

from const import PaymentStatus
from gate_nambaone.gate_nambaone import GateNambaOne
from models import SaleRequest

CREATE_PAYMENT_URL = (
    "https://provider.example"
    "/public/merchant/payment/v2"
    "/159e7e3b-94e1-48c7-bec5-952949f7935f"
    "/one-time"
)


def make_request(
    terminal_data: dict,
) -> SaleRequest:
    return SaleRequest(
        invoice_id="invoice-1001",
        amount=Decimal("10.50"),
        currency_code="KGS",
        finish_url="https://merchant.example/success",
        description="Test payment",
        terminal_data=terminal_data,
    )


@pytest.mark.asyncio
async def test_sale_without_card_success(
    gate: GateNambaOne,
    terminal_data: dict,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=CREATE_PAYMENT_URL,
        status_code=200,
        json={
            "status": "OK",
            "data": {
                "guid": (
                    "f49b4586-3c2d-48b9-abed-28219c02a1f2"
                ),
                "token": (
                    "https://app.nambaone.app/"
                    "#payment-token"
                ),
                "amount": "1050",
                "status": "ACTIVE",
                "currencyCode": "KGS",
            },
        },
    )

    response = await gate.sale_without_card(
        make_request(terminal_data),
    )

    assert response.status == PaymentStatus.PENDING
    assert response.amount == Decimal("10.50")
    assert response.currency_code == "KGS"
    assert response.external_id == "invoice-1001"
    assert response.redirect is not None
    assert response.redirect.url == (
        "https://app.nambaone.app/#payment-token"
    )
    assert response.code is None


@pytest.mark.asyncio
async def test_sale_without_card_provider_rejected_request(
    gate: GateNambaOne,
    terminal_data: dict,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=CREATE_PAYMENT_URL,
        status_code=200,
        json={
            "status": "ERROR",
            "data": None,
            "error": {
                "errorCode": (
                    "PAYMENT_LINK_EXTERNAL_ID_DUPLICATE_EXCEPTION"
                ),
                "message": "External ID already exists",
            },
        },
    )

    response = await gate.sale_without_card(
        make_request(terminal_data),
    )

    assert response.status == PaymentStatus.FAILED
    assert response.code == (
        "PAYMENT_LINK_EXTERNAL_ID_DUPLICATE_EXCEPTION"
    )
    assert response.message == "External ID already exists"


@pytest.mark.asyncio
async def test_sale_without_card_invalid_terminal_data(
    gate: GateNambaOne,
) -> None:
    request = SaleRequest(
        invoice_id="invoice-1001",
        amount=Decimal("10.50"),
        currency_code="KGS",
        terminal_data={
            "provider_base_url": "https://provider.example",
        },
    )

    response = await gate.sale_without_card(request)

    assert response.status == PaymentStatus.FAILED
    assert response.code == "validation_error"


@pytest.mark.asyncio
async def test_sale_without_card_invalid_provider_json(
    gate: GateNambaOne,
    terminal_data: dict,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=CREATE_PAYMENT_URL,
        status_code=200,
        content=b"not-json",
    )

    response = await gate.sale_without_card(
        make_request(terminal_data),
    )

    assert response.status == PaymentStatus.FAILED
    assert response.code == "invalid_provider_response"
    assert "invalid JSON" in response.message


@pytest.mark.asyncio
async def test_sale_without_card_empty_provider_response(
    gate: GateNambaOne,
    terminal_data: dict,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=CREATE_PAYMENT_URL,
        status_code=200,
        content=b"",
    )

    response = await gate.sale_without_card(
        make_request(terminal_data),
    )

    assert response.status == PaymentStatus.FAILED
    assert response.code == "invalid_provider_response"
    assert "empty HTTP response" in response.message


@pytest.mark.asyncio
async def test_sale_without_card_provider_timeout(
    gate: GateNambaOne,
    terminal_data: dict,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_exception(
        httpx.ReadTimeout("Provider timeout"),
    )

    response = await gate.sale_without_card(
        make_request(terminal_data),
    )

    assert response.status == PaymentStatus.FAILED
    assert response.code == "provider_timeout"