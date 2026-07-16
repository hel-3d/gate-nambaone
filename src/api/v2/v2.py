from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends

from api.deps import get_gate
from gate_nambaone.gate_nambaone import GateNambaOne
from models import RefundRequest
from models import RefundResponse
from models import RefundStatusRequest
from models import RefundStatusResponse
from models import SaleRequest
from models import SaleResponse
from models import StatusRequest
from models import StatusResponse

router = APIRouter(tags=["payments"])

GateDependency = Annotated[
    GateNambaOne,
    Depends(get_gate),
]


@router.post(
    "/sale_without_card",
    response_model=SaleResponse,
    summary="Create payment without card data",
)
async def sale_without_card(
    request: SaleRequest,
    gate: GateDependency,
) -> SaleResponse:
    return await gate.sale_without_card(request)


@router.post(
    "/status",
    response_model=StatusResponse,
    summary="Get payment status",
)
async def payment_status(
    request: StatusRequest,
    gate: GateDependency,
) -> StatusResponse:
    return await gate.status(request)


@router.post(
    "/refund",
    response_model=RefundResponse,
    summary="Create payment refund",
)
async def refund(
    request: RefundRequest,
    gate: GateDependency,
) -> RefundResponse:
    return await gate.refund(request)


@router.post(
    "/refund_status",
    response_model=RefundStatusResponse,
    summary="Get refund status",
)
async def refund_status(
    request: RefundStatusRequest,
    gate: GateDependency,
) -> RefundStatusResponse:
    return await gate.refund_status(request)