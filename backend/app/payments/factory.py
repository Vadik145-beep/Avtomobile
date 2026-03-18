from app.config import settings
from app.payments.base import BasePaymentProvider


def get_provider() -> BasePaymentProvider:
    """Return the configured payment provider instance."""
    provider = settings.payment_provider.lower()

    if provider == "stub":
        from app.payments.stub import StubProvider
        return StubProvider()

    if provider == "yukassa":
        from app.payments.yukassa import YooKassaProvider
        return YooKassaProvider()

    raise ValueError(
        f"Unknown payment provider: {provider!r}. "
        "Supported values: stub, yukassa."
    )
