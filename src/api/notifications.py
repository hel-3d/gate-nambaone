import json
import logging
from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Header
from fastapi import HTTPException
from fastapi import Request
from fastapi import status
from pydantic import ValidationError

from api.deps import get_gate
from gate_nambaone.gate_nambaone import GateNambaOne
from models import InvoiceNotificationResponse
from models import PaymentOrderWebhook
from provider_client import NambaOneClient
from settings import settings
from terminal_data import TerminalData

logger = logging.getLogger(__name__)

router = APIRouter(tags=["notifications"])

GateDependency = Annotated[
    GateNambaOne,
    Depends(get_gate),
]

SaltHeader = Annotated[
    str | None,
    Header(alias="x-merchant-api-salt"),
]

SignatureHeader = Annotated[
    str | None,
    Header(alias="x-merchant-api-signature"),
]


@router.post(
    "/invoice",
    response_model=InvoiceNotificationResponse,
    summary="Process Namba One payment webhook",
)
async def invoice_notification(
    request: Request,
    gate: GateDependency,
    salt: SaltHeader = None,
    signature: SignatureHeader = None,
) -> InvoiceNotificationResponse:
    raw_body = await request.body()

    try:
        body_text = raw_body.decode()
        payload = json.loads(body_text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_json",
                "message": "Webhook body is not valid JSON",
            },
        ) from exc

    merchant_account_guid = (
        payload.get("data", {}).get("merchantAccountGuid")
        or settings.NAMBAONE_MERCHANT_ID
    )

    if not settings.NAMBAONE_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "configuration_error",
                "message": "NAMBAONE_SECRET is not configured",
            },
        )

    try:
        terminal_data = TerminalData.model_validate(
            {
                "provider_base_url": settings.NAMBAONE_BASE_URL,
                "merchant_account_guid": merchant_account_guid,
                "secret": settings.NAMBAONE_SECRET,
            }
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "configuration_error",
                "message": "Namba One webhook configuration is invalid",
            },
        ) from exc

    if not salt or not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "missing_signature",
                "message": "Webhook signature headers are required",
            },
        )

    client = NambaOneClient(
        http_client=request.app.state.http_client,
        terminal_data=terminal_data,
    )

    if not client.verify_signature(
        path=request.url.path,
        body=body_text,
        salt=salt,
        signature=signature,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "invalid_signature",
                "message": "Webhook signature is invalid",
            },
        )

    try:
        notification = PaymentOrderWebhook.model_validate(payload)
    except ValidationError as exc:
        logger.warning(
            "Invalid payment webhook: %s",
            exc.errors(),
        )

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "validation_error",
                "message": "Webhook data is not valid",
                "details": exc.errors(),
            },
        ) from exc

    return await gate.invoice_notification(notification)