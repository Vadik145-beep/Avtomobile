"""
YooKassa payment provider.

To activate:
1. Set PAYMENT_PROVIDER=yukassa in .env
2. Set YUKASSA_SHOP_ID and YUKASSA_SECRET_KEY in .env
3. Install yookassa SDK: pip install yookassa
4. Replace NotImplementedError bodies with real SDK calls.

Reference: https://yookassa.ru/developers/api
"""

from app.payments.base import BasePaymentProvider, InvoiceResult, WebhookResult


class YooKassaProvider(BasePaymentProvider):
    async def create_invoice(self, tg_id: int, amount: int, package_id: str) -> InvoiceResult:
        raise NotImplementedError(
            "YooKassa integration not yet implemented. "
            "Set PAYMENT_PROVIDER=stub for testing."
        )

    async def verify_webhook(self, payload: dict) -> WebhookResult:
        raise NotImplementedError(
            "YooKassa webhook verification not yet implemented. "
            "Set PAYMENT_PROVIDER=stub for testing."
        )
