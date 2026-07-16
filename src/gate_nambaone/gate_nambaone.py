from typing import Any

import httpx
from pydantic import ValidationError

from const import PaymentStatus
from const import map_nambaone_status
from models import InvoiceNotificationResponse
from models import PaymentOrderWebhook
from models import Redirect
from models import RefundRequest
from models import RefundResponse
from models import RefundStatusRequest
from models import RefundStatusResponse
from models import SaleRequest
from models import SaleResponse
from models import StatusRequest
from models import StatusResponse
from provider_client import NambaOneClient
from provider_client import ProviderConnectionError
from provider_client import ProviderRejectedError
from provider_client import ProviderResponseError
from provider_client import ProviderTimeoutError
from provider_client import amount_from_minor_units
from provider_client import amount_to_minor_units
from terminal_data import TerminalData

PROVIDER_EXCEPTIONS = (
    ProviderTimeoutError,
    ProviderConnectionError,
    ProviderRejectedError,
    ProviderResponseError,
)


class GateNambaOne:
    def __init__(
        self,
        httpx_client: httpx.AsyncClient,
        **_: Any,
    ) -> None:
        self.http_client = httpx_client

    @staticmethod
    def _parse_terminal_data(
        value: dict[str, Any],
    ) -> TerminalData:
        return TerminalData.model_validate(value)

    def _client(
        self,
        terminal_data: TerminalData,
    ) -> NambaOneClient:
        return NambaOneClient(
            http_client=self.http_client,
            terminal_data=terminal_data,
        )

    @staticmethod
    def _provider_error(
        exc: Exception,
    ) -> tuple[str, str]:
        if isinstance(exc, ProviderTimeoutError):
            return "provider_timeout", "Namba One did not respond in time"

        if isinstance(exc, ProviderConnectionError):
            return (
                "provider_connection_error",
                "Could not connect to Namba One",
            )

        if isinstance(exc, ProviderRejectedError):
            return exc.code, str(exc)

        if isinstance(exc, ProviderResponseError):
            return "invalid_provider_response", str(exc)

        return "provider_error", "Unexpected Namba One error"

    async def sale_without_card(
        self,
        req: SaleRequest,
    ) -> SaleResponse:
        try:
            terminal_data = self._parse_terminal_data(
                req.terminal_data,
            )
            amount_minor = amount_to_minor_units(req.amount)
        except (ValidationError, ValueError) as exc:
            return SaleResponse(
                status=PaymentStatus.FAILED,
                amount=req.amount,
                currency_code=req.currency_code,
                code="validation_error",
                message=str(exc),
            )

        try:
            data = await self._client(
                terminal_data
            ).create_payment(
                external_id=req.invoice_id,
                amount_minor=amount_minor,
                description=req.description,
                finish_url=req.finish_url,
            )
        except PROVIDER_EXCEPTIONS as exc:
            code, message = self._provider_error(exc)

            return SaleResponse(
                status=PaymentStatus.FAILED,
                amount=req.amount,
                currency_code=req.currency_code,
                code=code,
                message=message,
            )

        payment_link_guid = data.get("guid")
        token = data.get("token")

        if not payment_link_guid or not token:
            return SaleResponse(
                status=PaymentStatus.FAILED,
                amount=req.amount,
                currency_code=req.currency_code,
                code="invalid_provider_response",
                message=(
                    "Namba One response does not contain "
                    "payment-link guid or token"
                ),
            )

        return SaleResponse(
            status=PaymentStatus.PENDING,
            amount=amount_from_minor_units(
                data.get("amount", amount_minor)
            ),
            currency_code=str(
                data.get("currencyCode", "KGS")
            ),
            # Для status нужен externalId, которым является invoice_id.
            external_id=req.invoice_id,
            redirect=Redirect(
                url=str(token),
                method="GET",
            ),
        )

    async def status(
        self,
        req: StatusRequest,
    ) -> StatusResponse:
        try:
            terminal_data = self._parse_terminal_data(
                req.terminal_data,
            )
        except ValidationError as exc:
            return StatusResponse(
                status=PaymentStatus.FAILED,
                currency_code=req.currency_code,
                code="validation_error",
                message=str(exc),
            )

        external_id = req.external_id or req.invoice_id

        try:
            data = await self._client(
                terminal_data
            ).get_payment(external_id)
        except PROVIDER_EXCEPTIONS as exc:
            code, message = self._provider_error(exc)

            return StatusResponse(
                status=PaymentStatus.PENDING,
                currency_code=req.currency_code,
                external_id=external_id,
                code=code,
                message=message,
            )

        if data is None:
            return StatusResponse(
                status=PaymentStatus.PENDING,
                amount=None,
                currency_code=req.currency_code,
                external_id=external_id,
            )

        return StatusResponse(
            status=map_nambaone_status(
                str(data.get("status", ""))
            ),
            amount=amount_from_minor_units(
                data.get("paymentAmount")
                or data.get("amount")
                or "0"
            ),
            currency_code=str(
                data.get("currency", "KGS")
            ),
            # GUID фактического payment order нужен для refund.
            external_id=str(data.get("guid") or external_id),
        )

    async def refund(
        self,
        req: RefundRequest,
    ) -> RefundResponse:
        try:
            terminal_data = self._parse_terminal_data(
                req.terminal_data,
            )
            amount_minor = amount_to_minor_units(req.amount)
        except (ValidationError, ValueError) as exc:
            return RefundResponse(
                status=PaymentStatus.FAILED,
                amount=req.amount,
                currency_code=req.currency_code,
                external_id=req.external_id,
                code="validation_error",
                message=str(exc),
            )

        try:
            data = await self._client(
                terminal_data
            ).create_refund(
                payment_order_guid=req.external_id,
                external_refund_id=req.refund_id,
                amount_minor=amount_minor,
                reason=req.reason,
                requisite=req.requisite,
            )
        except PROVIDER_EXCEPTIONS as exc:
            code, message = self._provider_error(exc)

            return RefundResponse(
                status=PaymentStatus.FAILED,
                amount=req.amount,
                currency_code=req.currency_code,
                external_id=req.external_id,
                code=code,
                message=message,
            )

        return RefundResponse(
            status=map_nambaone_status(
                str(data.get("status", "CREATED"))
            ),
            amount=amount_from_minor_units(
                data.get("amount", amount_minor)
            ),
            currency_code=str(
                data.get("currency", "KGS")
            ),
            external_id=str(
                data.get("parentPaymentGuid")
                or req.external_id
            ),
            # extRefundId остаётся стабильным идентификатором status-запроса.
            refund_external_id=str(
                data.get("externalGuid")
                or req.refund_id
            ),
        )

    async def refund_status(
        self,
        req: RefundStatusRequest,
    ) -> RefundStatusResponse:
        try:
            terminal_data = self._parse_terminal_data(
                req.terminal_data,
            )
        except ValidationError as exc:
            return RefundStatusResponse(
                status=PaymentStatus.FAILED,
                currency_code=req.currency_code,
                external_id=req.external_id,
                refund_external_id=req.refund_external_id,
                code="validation_error",
                message=str(exc),
            )

        external_refund_id = (
            req.refund_external_id
            or req.refund_id
        )

        try:
            data = await self._client(
                terminal_data
            ).get_refund(external_refund_id)
        except PROVIDER_EXCEPTIONS as exc:
            code, message = self._provider_error(exc)

            return RefundStatusResponse(
                status=PaymentStatus.PENDING,
                currency_code=req.currency_code,
                external_id=req.external_id,
                refund_external_id=external_refund_id,
                code=code,
                message=message,
            )

        error_code = data.get("errorCode")

        return RefundStatusResponse(
            status=map_nambaone_status(
                str(data.get("status", ""))
            ),
            amount=amount_from_minor_units(
                data.get("amount", "0")
            ),
            currency_code=str(
                data.get("currency", "KGS")
            ),
            external_id=str(
                data.get("parentPaymentGuid")
                or req.external_id
                or ""
            )
            or None,
            refund_external_id=str(
                data.get("externalGuid")
                or external_refund_id
            ),
            code=str(error_code) if error_code else None,
            message=(
                {
                    "01": "Requisite not found",
                    "02": "Provider unavailable",
                    "03": "Unrecognized provider response",
                }.get(str(error_code))
                if error_code
                else None
            ),
        )

    async def invoice_notification(
        self,
        notification: PaymentOrderWebhook,
    ) -> InvoiceNotificationResponse:
        return InvoiceNotificationResponse(
            accepted=True,
            status=map_nambaone_status(
                notification.data.status
            ),
            payment_id=notification.data.guid,
            merchant_payment_id=notification.data.external_id,
        )


def get_gate_nambaone(
    **kwargs: Any,
) -> GateNambaOne:
    return GateNambaOne(**kwargs)