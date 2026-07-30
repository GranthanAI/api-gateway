from pydantic_settings import BaseSettings, SettingsConfigDict

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
    GRAPH_SERVICE_URL: str = "http://localhost:8000"

    JWT_SECRET_KEY: str = "supersecretjwtkeyforauthservicelocaldvelopment12345"
    JWT_ALGORITHM: str = "HS256"

settings = Settings()
