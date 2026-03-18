import uuid

from app.payments.base import BasePaymentProvider, InvoiceResult, WebhookResult
from app.payments.packages import get_package_limits


class StubProvider(BasePaymentProvider):
    """
    Stub payment provider for testing and development.
    Immediately confirms every payment without contacting any external service.
    invoice_url is always None — crediting happens inline in the buy endpoint.
    """

    async def create_invoice(self, tg_id: int, amount: int, package_id: str) -> InvoiceResult:
        payment_id = str(uuid.uuid4())
        limits = get_package_limits(package_id)
        return InvoiceResult(
            payment_id=payment_id,
            invoice_url=None,
            amount=limits,
        )

    async def verify_webhook(self, payload: dict) -> WebhookResult:
        """
        Stub webhook: accepts any payload that contains tg_id, payment_id, amount.
        Always returns verified=True.
        """
        try:
            tg_id = int(payload["tg_id"])
            payment_id = str(payload["payment_id"])
            amount = int(payload["amount"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid stub webhook payload: {exc}") from exc

        return WebhookResult(
            payment_id=payment_id,
            tg_id=tg_id,
            amount=amount,
            verified=True,
        )
