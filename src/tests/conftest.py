from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
import pytest_asyncio

from gate_nambaone.gate_nambaone import GateNambaOne


@pytest.fixture
def terminal_data() -> dict[str, Any]:
    return {
        "provider_base_url": "https://provider.example",
        "merchant_account_guid": (
            "159e7e3b-94e1-48c7-bec5-952949f7935f"
        ),
        "secret": "test-secret",
        "webhook_url": (
            "https://merchant.example/notifications/invoice"
        ),
        "refund_webhook_url": (
            "https://merchant.example/notifications/refund"
        ),
    }


@pytest_asyncio.fixture
async def http_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient() as client:
        yield client


@pytest.fixture
def gate(
    http_client: httpx.AsyncClient,
) -> GateNambaOne:
    return GateNambaOne(
        httpx_client=http_client,
    )