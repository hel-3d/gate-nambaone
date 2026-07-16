from enum import StrEnum


class PaymentStatus(StrEnum):
    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"
    REFUNDED = "refunded"


NAMBAONE_STATUS_MAPPING: dict[str, PaymentStatus] = {
    # Payment link
    "ACTIVE": PaymentStatus.PENDING,

    # Payment order
    "CREATED": PaymentStatus.PENDING,
    "PAYER_DEBIT": PaymentStatus.PENDING,
    "PAYER_DEBIT_SUCCESSFUL": PaymentStatus.PENDING,
    "PROCESSING": PaymentStatus.PENDING,
    "CANCELLATION_ATTEMPTED": PaymentStatus.PENDING,

    "COMPLETED": PaymentStatus.COMPLETE,
    "REFUNDED": PaymentStatus.REFUNDED,

    "CANCELED": PaymentStatus.FAILED,
    "FAILED": PaymentStatus.FAILED,
    "EXPIRED": PaymentStatus.FAILED,
    "CANCELLATION_FAILED": PaymentStatus.FAILED,
    "STUCK": PaymentStatus.FAILED,
}


def map_nambaone_status(value: str | None) -> PaymentStatus:
    if not value:
        return PaymentStatus.PENDING

    return NAMBAONE_STATUS_MAPPING.get(
        value.strip().upper(),
        PaymentStatus.PENDING,
    )