from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str
    backend_url: str = "http://backend:8000"
    bot_internal_secret: str = ""
    redis_url: str = "redis://redis:6379"
    miniapp_url: str = "https://yourdomain.com/miniapp"


settings = Settings()
