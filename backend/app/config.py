from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://avto_lead:password@postgres:5432/avto_lead"
    redis_url: str = "redis://redis:6379"
    secret_key: str = "change-me-in-production"
    admin_jwt_expire_hours: int = 8

    # Admin credentials
    admin_username: str = "admin"
    # Store as bcrypt hash; generate with: python -c "from passlib.context import CryptContext; print(CryptContext(['bcrypt']).hash('yourpassword'))"
    admin_password_hash: str = "$2b$12$placeholder_replace_me"

    # Webhook / internal secrets
    lidozvon_secret: str = ""
    bot_internal_secret: str = ""

    # Telegram Bot Token (used to validate Mini App initData)
    bot_token: str = ""

    # Payments
    payment_provider: str = "stub"  # "stub" | "yukassa"
    yukassa_shop_id: str = ""
    yukassa_secret_key: str = ""

    # Public domain (used for Telegram webhook URL)
    domain: str = "https://yourdomain.com"


settings = Settings()
