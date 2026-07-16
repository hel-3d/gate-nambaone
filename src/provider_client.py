import base64
import hashlib
import hmac
import json
import uuid
from decimal import Decimal
from typing import Any

import httpx

from terminal_data import TerminalData


class ProviderError(Exception):
    """Base exception for Namba One integration."""


class ProviderTimeoutError(ProviderError):
    """Namba One did not respond before timeout."""


class ProviderConnectionError(ProviderError):
    """Connection to Namba One failed."""


class ProviderResponseError(ProviderError):
    """Namba One returned an invalid response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_data: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class ProviderRejectedError(ProviderError):
    """Namba One returned a valid API error."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "provider_rejected",
        status_code: int | None = None,
        response_data: Any = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.response_data = response_data


class NambaOneClient:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        terminal_data: TerminalData,
    ) -> None:
        self.http_client = http_client
        self.terminal_data = terminal_data

    @staticmethod
    def serialize_json(payload: dict[str, Any]) -> str:
        """
        Namba One signs the exact JSON string sent in the request.

        Compact separators are used so the signed value and transmitted body
        are guaranteed to be identical.
        """
        return json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    def make_signature(
        self,
        path: str,
        body: str,
        salt: str,
    ) -> str:
        message = f"{path}{body}{salt}".encode()

        digest = hmac.new(
            self.terminal_data.secret.encode("utf-8"),
            message,
            hashlib.sha512,
        ).digest()

        return base64.b64encode(digest).decode("ascii")

    def verify_signature(
        self,
        *,
        path: str,
        body: str,
        salt: str,
        signature: str,
    ) -> bool:
        expected = self.make_signature(
            path=path,
            body=body,
            salt=salt,
        )

        return hmac.compare_digest(expected, signature)

    def _signed_headers(
        self,
        *,
        path: str,
        body: str,
    ) -> dict[str, str]:
        salt = str(uuid.uuid4())

        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-merchant-api-salt": salt,
            "x-merchant-api-signature": self.make_signature(
                path=path,
                body=body,
                salt=salt,
            ),
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        method = method.upper()

        # GET-запрос подписывается с пустой строкой вместо тела.
        body = (
            self.serialize_json(payload)
            if payload is not None
            else ""
        )

        headers = self._signed_headers(
            path=path,
            body=body,
        )

        try:
            response = await self.http_client.request(
                method=method,
                url=self.terminal_data.build_url(path),
                content=body.encode("utf-8") if body else None,
                headers=headers,
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                "Namba One request timed out",
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderConnectionError(
                f"Namba One request failed: {exc}",
            ) from exc

        if not response.content:
            raise ProviderResponseError(
                "Namba One returned an empty HTTP response",
                status_code=response.status_code,
            )

        try:
            response_data = response.json()
        except ValueError as exc:
            raise ProviderResponseError(
                "Namba One returned invalid JSON",
                status_code=response.status_code,
                response_data=response.text,
            ) from exc

        if not isinstance(response_data, dict):
            raise ProviderResponseError(
                "Namba One returned an unexpected response structure",
                status_code=response.status_code,
                response_data=response_data,
            )

        api_status = str(
            response_data.get("status", "")
        ).upper()

        if response.is_error or api_status == "ERROR":
            error = response_data.get("error")

            if isinstance(error, dict):
                error_code = str(
                    error.get("errorCode")
                    or "provider_error"
                )
                error_message = str(
                    error.get("message")
                    or error_code
                )
            else:
                error_code = "provider_error"
                error_message = "Namba One rejected the request"

            raise ProviderRejectedError(
                error_message,
                code=error_code,
                status_code=response.status_code,
                response_data=response_data,
            )

        if api_status != "OK":
            raise ProviderResponseError(
                "Namba One response does not contain status OK",
                status_code=response.status_code,
                response_data=response_data,
            )

        return response_data

    async def create_payment(
        self,
        *,
        external_id: str,
        amount_minor: str,
        description: str | None,
        finish_url: str | None,
    ) -> dict[str, Any]:
        path = self.terminal_data.format_path(
            self.terminal_data.create_payment_path,
        )

        payload: dict[str, Any] = {
            "externalId": external_id,
            "amount": amount_minor,
            "amountCanBeChanged": False,
        }

        if self.terminal_data.webhook_url:
            payload["webhookUrl"] = str(
                self.terminal_data.webhook_url
            )

        if description:
            payload["comment"] = description

        if self.terminal_data.merchant_employee_guid:
            payload["merchantEmployeeGuid"] = (
                self.terminal_data.merchant_employee_guid
            )

        if self.terminal_data.acceptor_merchant_account_guid:
            payload["acceptorMerchantAccountGuid"] = (
                self.terminal_data.acceptor_merchant_account_guid
            )
        elif self.terminal_data.acceptor_merchant_account_token:
            payload["acceptorMerchantAccountToken"] = (
                self.terminal_data.acceptor_merchant_account_token
            )

        if finish_url:
            payload["webOptions"] = {
                "redirectLink": finish_url,
                "autoRedirect": True,
            }

        response = await self._request(
            "POST",
            path,
            payload=payload,
        )

        data = response.get("data")

        if not isinstance(data, dict):
            raise ProviderResponseError(
                "Namba One create-payment response has no data object",
                response_data=response,
            )

        return data

    async def get_payment(
        self,
        external_id: str,
    ) -> dict[str, Any] | None:
        path = self.terminal_data.format_path(
            self.terminal_data.payment_status_path,
            external_id=external_id,
        )

        response = await self._request(
            "GET",
            path,
        )

        data = response.get("data")

        # Согласно документации status=OK без data означает,
        # что платеж по QR ещё не был произведён.
        if data is None:
            return None

        if not isinstance(data, dict):
            raise ProviderResponseError(
                "Namba One payment-status response contains invalid data",
                response_data=response,
            )

        return data

    async def create_refund(
        self,
        *,
        payment_order_guid: str,
        external_refund_id: str,
        amount_minor: str,
        reason: str | None,
        requisite: str | None = None,
    ) -> dict[str, Any]:
        path = self.terminal_data.format_path(
            self.terminal_data.create_refund_path,
            external_refund_id=external_refund_id,
        )

        webhook_url = (
            self.terminal_data.refund_webhook_url
            or self.terminal_data.webhook_url
        )

        payload: dict[str, Any] = {
            "parentType": "PAYMENT_QR",
            "paymentOrderGuid": payment_order_guid,
            "amount": amount_minor,
            "comment": reason or "Refund",
        }

        if webhook_url:
            payload["webhookUrl"] = str(webhook_url)

        if requisite:
            payload["requisite"] = requisite

        response = await self._request(
            "POST",
            path,
            payload=payload,
        )

        data = response.get("data")

        if not isinstance(data, dict):
            raise ProviderResponseError(
                "Namba One create-refund response has no data object",
                response_data=response,
            )

        return data

    async def get_refund(
        self,
        external_refund_id: str,
    ) -> dict[str, Any]:
        path = self.terminal_data.format_path(
            self.terminal_data.refund_status_path,
            external_refund_id=external_refund_id,
        )

        response = await self._request(
            "GET",
            path,
        )

        data = response.get("data")

        if not isinstance(data, dict):
            raise ProviderResponseError(
                "Namba One refund-status response has no data object",
                response_data=response,
            )

        return data


def amount_to_minor_units(amount: Decimal) -> str:
    """
    Namba One expects KGS amounts in tyiyn.

    10.50 KGS -> "1050"
    """
    minor = amount * Decimal("100")

    if minor != minor.to_integral_value():
        raise ValueError(
            "Amount must contain no more than two decimal places"
        )

    return str(int(minor))


def amount_from_minor_units(value: Any) -> Decimal:
    return Decimal(str(value)) / Decimal("100")