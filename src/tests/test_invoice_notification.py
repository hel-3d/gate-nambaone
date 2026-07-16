from datetime import UTC
from datetime import datetime

import pytest

from const import PaymentStatus
from gate_nambaone.gate_nambaone import GateNambaOne
from models import PaymentOrderWebhook


@pytest.mark.asyncio
async def test_invoice_notification_success(
    gate: GateNambaOne,
) -> None:
    notification = PaymentOrderWebhook.model_validate(
        {
            "createdAt": datetime.now(UTC).isoformat(),
            "data": {
                "guid": "payment-guid",
                "externalId": "invoice-1001",
                "channel": "BALANCE",
                "paymentLinkGuid": "payment-link-guid",
                "merchantAccountGuid": "merchant-guid",
                "currency": "KGS",
                "amount": "1050",
                "paymentAmount": "1050",
                "refundAmount": "0",
                "remark": "Payment",
                "customerGuid": "customer-guid",
                "maskedPhoneNumber": "**********622",
                "status": "COMPLETED",
                "createdAt": datetime.now(UTC).isoformat(),
                "settledAt": datetime.now(UTC).isoformat(),
                "type": "PAYMENT_QR",
            },
            "type": "PAYMENT_ORDER",
            "version": "1",
        }
    )

    response = await gate.invoice_notification(notification)

    assert response.accepted is True
    assert response.status == PaymentStatus.COMPLETE
    assert response.payment_id == "payment-guid"
    assert response.merchant_payment_id == "invoice-1001"


@pytest.mark.asyncio
async def test_invoice_notification_failed_payment(
    gate: GateNambaOne,
) -> None:
    notification = PaymentOrderWebhook.model_validate(
        {
            "createdAt": datetime.now(UTC).isoformat(),
            "data": {
                "guid": "payment-guid",
                "externalId": "invoice-1001",
                "merchantAccountGuid": "merchant-guid",
                "currency": "KGS",
                "amount": "1050",
                "paymentAmount": "0",
                "refundAmount": "0",
                "status": "FAILED",
                "createdAt": datetime.now(UTC).isoformat(),
                "settledAt": datetime.now(UTC).isoformat(),
                "type": "PAYMENT_QR",
            },
            "type": "PAYMENT_ORDER",
            "version": "1",
        }
    )

    response = await gate.invoice_notification(notification)

    assert response.accepted is True
    assert response.status == PaymentStatus.FAILED


def test_invoice_notification_invalid_request() -> None:
    with pytest.raises(ValueError):
        PaymentOrderWebhook.model_validate(
            {
                "type": "PAYMENT_ORDER",
                "version": "1",
                "data": {
                    "status": "COMPLETED",
                },
            }
        )