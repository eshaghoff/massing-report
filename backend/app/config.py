from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/nyc_zoning"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/nyc_zoning"
    redis_url: str = "redis://localhost:6379"
    nyc_geoclient_app_id: str = ""
    nyc_geoclient_app_key: str = ""
    google_maps_api_key: str = ""
    socrata_app_token: str = ""
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://100.67.179.5:3000",
        "https://massingreport.com",
        "https://www.massingreport.com",
        "https://massing-report.vercel.app",
        "https://massing-report-eae2jv83a-eshaghoffs-projects.vercel.app",
    ]

    # Clerk auth
    clerk_domain: str = ""  # e.g. "your-app.clerk.accounts.dev"
    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""

    # Stripe payments
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_annual_price_id: str = ""  # Stripe Price ID for $10K/year plan

    # Frontend URL (for Stripe redirect URLs)
    frontend_url: str = "https://massingreport.com"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
