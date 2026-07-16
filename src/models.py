from datetime import datetime
from decimal import Decimal
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

from const import PaymentStatus


class APIModel(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class Redirect(APIModel):
    url: str
    method: str = "GET"
    payload: dict[str, Any] | list[Any] | None = None


class SaleRequest(APIModel):
    invoice_id: str = Field(min_length=1, max_length=128)
    amount: Decimal = Field(gt=0)
    currency_code: str = Field(min_length=3, max_length=3)
    finish_url: str | None = None
    description: str | None = Field(default=None, max_length=512)
    terminal_data: dict[str, Any]

    @field_validator("currency_code")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        value = value.upper()

        if value != "KGS":
            raise ValueError("Namba One supports KGS only")

        return value


class SaleResponse(APIModel):
    status: PaymentStatus
    amount: Decimal
    currency_code: str
    external_id: str | None = None
    redirect: Redirect | None = None
    code: str | None = None
    message: str | None = None


class StatusRequest(APIModel):
    invoice_id: str = Field(min_length=1, max_length=128)
    external_id: str | None = None
    currency_code: str = Field(min_length=3, max_length=3)
    terminal_data: dict[str, Any]

    @field_validator("currency_code")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        value = value.upper()

        if value != "KGS":
            raise ValueError("Namba One supports KGS only")

        return value


class StatusResponse(APIModel):
    status: PaymentStatus
    amount: Decimal | None = None
    currency_code: str
    external_id: str | None = None
    rrn: str | None = None
    code: str | None = None
    message: str | None = None


class RefundRequest(APIModel):
    refund_id: str = Field(min_length=1, max_length=128)
    invoice_id: str = Field(min_length=1, max_length=128)

    # GUID совершённого платежного ордера Namba One.
    external_id: str = Field(min_length=1, max_length=128)

    amount: Decimal = Field(gt=0)
    currency_code: str = Field(min_length=3, max_length=3)
    reason: str | None = Field(default=None, max_length=512)
    requisite: str | None = Field(default=None, max_length=128)
    terminal_data: dict[str, Any]

    @field_validator("currency_code")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        value = value.upper()

        if value != "KGS":
            raise ValueError("Namba One supports KGS only")

        return value


class RefundResponse(APIModel):
    status: PaymentStatus
    amount: Decimal
    currency_code: str
    external_id: str | None = None
    refund_external_id: str | None = None
    code: str | None = None
    message: str | None = None


class RefundStatusRequest(APIModel):
    refund_id: str = Field(min_length=1, max_length=128)
    refund_external_id: str | None = None
    external_id: str | None = None
    currency_code: str = Field(min_length=3, max_length=3)
    terminal_data: dict[str, Any]

    @field_validator("currency_code")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        value = value.upper()

        if value != "KGS":
            raise ValueError("Namba One supports KGS only")

        return value


class RefundStatusResponse(APIModel):
    status: PaymentStatus
    amount: Decimal | None = None
    currency_code: str
    external_id: str | None = None
    refund_external_id: str | None = None
    code: str | None = None
    message: str | None = None


class PaymentWebhookData(APIModel):
    guid: str
    external_id: str = Field(alias="externalId")
    channel: str | None = None
    payment_link_guid: str | None = Field(
        default=None,
        alias="paymentLinkGuid",
    )
    merchant_account_guid: str = Field(
        alias="merchantAccountGuid",
    )
    currency: str
    amount: Decimal
    payment_amount: Decimal = Field(alias="paymentAmount")
    refund_amount: Decimal = Field(alias="refundAmount")
    remark: str | None = None
    customer_guid: str | None = Field(
        default=None,
        alias="customerGuid",
    )
    masked_phone_number: str | None = Field(
        default=None,
        alias="maskedPhoneNumber",
    )
    status: str
    created_at: datetime = Field(alias="createdAt")
    settled_at: datetime | None = Field(
        default=None,
        alias="settledAt",
    )
    type: str


class PaymentOrderWebhook(APIModel):
    created_at: datetime = Field(alias="createdAt")
    data: PaymentWebhookData
    type: Literal["PAYMENT_ORDER"]
    version: str


class RefundWebhookData(APIModel):
    guid: str
    external_guid: str = Field(alias="externalGuid")
    parent_payment_guid: str = Field(alias="parentPaymentGuid")
    merchant_account_guid: str = Field(
        alias="merchantAccountGuid",
    )
    currency: str
    amount: Decimal
    status: str
    webhook_url: str | None = Field(
        default=None,
        alias="webhookUrl",
    )
    version: str


class RefundOrderWebhook(APIModel):
    created_at: datetime = Field(alias="createdAt")
    data: RefundWebhookData
    type: Literal["REFUND_ORDER"]
    version: str


class InvoiceNotificationResponse(APIModel):
    accepted: bool = True
    status: PaymentStatus
    payment_id: str
    merchant_payment_id: str