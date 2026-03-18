from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class InvoiceResult:
    payment_id: str
    invoice_url: str | None  # None for stub / immediate providers
    amount: int


@dataclass
class WebhookResult:
    payment_id: str
    tg_id: int
    amount: int
    verified: bool


class BasePaymentProvider(ABC):
    @abstractmethod
    async def create_invoice(self, tg_id: int, amount: int, package_id: str) -> InvoiceResult:
        """
        Initiate a payment intent. Returns InvoiceResult with a payment_id and
        an optional invoice_url to redirect the user to. For providers that support
        immediate crediting (stub), invoice_url is None and crediting happens inline.
        """

    @abstractmethod
    async def verify_webhook(self, payload: dict) -> WebhookResult:
        """
        Validate and parse an incoming payment provider webhook payload.
        Returns WebhookResult with verified=True when the payment is confirmed.
        Raises ValueError if the payload is invalid or the signature doesn't match.
        """
