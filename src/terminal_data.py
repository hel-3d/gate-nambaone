from urllib.parse import urljoin

from pydantic import AliasChoices
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import HttpUrl
from pydantic import field_validator


class TerminalData(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    provider_base_url: HttpUrl = Field(
        validation_alias=AliasChoices(
            "provider_base_url",
            "base_url",
        ),
    )

    merchant_account_guid: str = Field(
        min_length=1,
        validation_alias=AliasChoices(
            "merchant_account_guid",
            "merchantAccountGuid",
            "merchant_id",
            "provider_merchant_id",
            "provider_api_key",
        ),
    )

    secret: str = Field(
        min_length=1,
        validation_alias=AliasChoices(
            "secret",
            "provider_secret",
            "provider_secret_key",
        ),
    )

    webhook_url: HttpUrl | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "webhook_url",
            "callback_url",
            "provider_callback_url_invoice",
        ),
    )

    refund_webhook_url: HttpUrl | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "refund_webhook_url",
            "provider_callback_url_refund",
        ),
    )

    merchant_employee_guid: str | None = None
    acceptor_merchant_account_guid: str | None = None
    acceptor_merchant_account_token: str | None = None
    proxy_url: str | None = None

    create_payment_path: str = (
        "/public/merchant/payment/v2/"
        "{merchant_account_guid}/one-time"
    )
    payment_status_path: str = (
        "/public/merchant/payment/v1/"
        "{merchant_account_guid}/one-time/{external_id}"
    )
    create_refund_path: str = (
        "/public/merchant/payment/v1/"
        "{merchant_account_guid}/refund/{external_refund_id}"
    )
    refund_status_path: str = (
        "/public/merchant/payment/v1/"
        "{merchant_account_guid}/refund/{external_refund_id}"
    )

    @field_validator(
        "create_payment_path",
        "payment_status_path",
        "create_refund_path",
        "refund_status_path",
    )
    @classmethod
    def normalize_path(cls, value: str) -> str:
        return value if value.startswith("/") else f"/{value}"

    @property
    def base_url(self) -> str:
        return str(self.provider_base_url).rstrip("/") + "/"

    def build_url(self, path: str) -> str:
        return urljoin(
            self.base_url,
            path.lstrip("/"),
        )

    def format_path(
        self,
        template: str,
        **values: str,
    ) -> str:
        return template.format(
            merchant_account_guid=self.merchant_account_guid,
            **values,
        )