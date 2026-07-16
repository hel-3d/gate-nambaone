import httpx
from fastapi import Request

from gate_nambaone.gate_nambaone import GateNambaOne


def get_http_client(request: Request) -> httpx.AsyncClient:
    client: httpx.AsyncClient = request.app.state.http_client
    return client


def get_gate(request: Request) -> GateNambaOne:
    return GateNambaOne(
        http_client=get_http_client(request),
    )