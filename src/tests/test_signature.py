import base64
import hashlib
import hmac

import httpx

from provider_client import NambaOneClient
from terminal_data import TerminalData

PATH = (
    "/public/merchant/payment/v1/"
    "39b826bf-6b00-4996-bee7-7bfab4e055f5/static"
)

BODY = (
    '{"externalId":"123",'
    '"webhookUrl":"http://test.test.test",'
    '"amount":"100",'
    '"amountCanBeChanged":false}'
)

SALT = "d5afd864-7559-43d3-9f30-76805f536db9"
SECRET = "some secret from Namba One team"


def make_client() -> NambaOneClient:
    terminal_data = TerminalData(
        provider_base_url="https://provider.example",
        merchant_account_guid=(
            "39b826bf-6b00-4996-bee7-7bfab4e055f5"
        ),
        secret=SECRET,
    )

    return NambaOneClient(
        http_client=httpx.AsyncClient(),
        terminal_data=terminal_data,
    )


def test_signature_uses_hmac_sha512_and_base64() -> None:
    client = make_client()

    expected_digest = hmac.new(
        SECRET.encode(),
        f"{PATH}{BODY}{SALT}".encode(),
        hashlib.sha512,
    ).digest()

    expected_signature = base64.b64encode(
        expected_digest
    ).decode()

    actual_signature = client.make_signature(
        path=PATH,
        body=BODY,
        salt=SALT,
    )

    assert actual_signature == expected_signature


def test_valid_signature_is_accepted() -> None:
    client = make_client()

    signature = client.make_signature(
        path=PATH,
        body=BODY,
        salt=SALT,
    )

    assert client.verify_signature(
        path=PATH,
        body=BODY,
        salt=SALT,
        signature=signature,
    )


def test_modified_body_invalidates_signature() -> None:
    client = make_client()

    signature = client.make_signature(
        path=PATH,
        body=BODY,
        salt=SALT,
    )

    assert not client.verify_signature(
        path=PATH,
        body=f"{BODY} ",
        salt=SALT,
        signature=signature,
    )