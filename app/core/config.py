from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    ENVIRONMENT: str = "development"
    PORT: int = 8080

    AUTH_SERVICE_URL: str = "http://localhost:8001"
    CONVERSATION_SERVICE_URL: str = "http://localhost:8002"
    LLM_SERVICE_URL: str = "http://localhost:8003"
    GRAPH_SERVICE_URL: str = "http://localhost:8000"
    MEMORY_SERVICE_URL: str = "http://localhost:8004"
    FILE_SERVICE_URL: str = "http://localhost:8006"

    # Comma-separated browser origins allowed by CORS. Empty = the localhost
    # dev-server origins when ENVIRONMENT != production, and NO cross-origin
    # access in production. "*" is accepted only outside production, and then
    # without credentials.
    CORS_ALLOW_ORIGINS: str = ""

    JWT_SECRET_KEY: str = "supersecretjwtkeyforauthservicelocaldvelopment12345"
    JWT_ALGORITHM: str = "HS256"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.strip().lower() in ("production", "prod")

    @property
    def cors_allow_origins(self) -> list[str]:
        origins = [o.strip() for o in self.CORS_ALLOW_ORIGINS.split(",") if o.strip()]
        if "*" in origins and self.is_production:
            raise ValueError("CORS_ALLOW_ORIGINS must list explicit origins in production; '*' is not allowed")
        if not origins and not self.is_production:
            return DEV_CORS_ORIGINS
        return origins

    @property
    def cors_allow_credentials(self) -> bool:
        # Browsers reject "*" together with credentials, so never combine them.
        return "*" not in self.cors_allow_origins

settings = Settings()
