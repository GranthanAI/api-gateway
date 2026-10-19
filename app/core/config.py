from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(hide_input_in_errors=True, 
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    ENVIRONMENT: str = "development"
    PORT: int = 8080
    # Largest request body the gateway accepts (bytes). API bodies are small JSON; uploads bypass the gateway.
    MAX_REQUEST_BODY_BYTES: int = 1_048_576

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
    # Issuer every access token must carry (auth-service always sets it). Tokens from any other issuer are rejected.
    JWT_ISSUER: str = "https://auth.granthan.com"

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

    @model_validator(mode="after")
    def _fail_fast_on_unsafe_production_config(self):
        """In production the service refuses to start with a development default or a weak secret (a known default
        would let anyone forge tokens). Development and test environments are unaffected. Secret VALUES are never
        included in the error message."""
        if self.ENVIRONMENT.strip().lower() not in ("production", "prod"):
            return self
        dev_values = {"supersecretjwtkeyforauthservicelocaldvelopment12345", "graphgpt-jwt-secret", "graphgpt-memory-secret", "changeme", "secret"}
        problems: list[str] = []

        def secret(name: str, value: str) -> None:
            if not value or value in dev_values or len(value) < 32:
                problems.append(f"{name} must be set to a unique secret of at least 32 characters")
        secret("JWT_SECRET_KEY", self.JWT_SECRET_KEY)
        if self.JWT_ALGORITHM not in ("HS256", "HS384", "HS512"):
            problems.append("JWT_ALGORITHM must be an HMAC algorithm (HS256/HS384/HS512)")
        if problems:
            raise ValueError("Unsafe production configuration: " + "; ".join(problems))
        return self


settings = Settings()
