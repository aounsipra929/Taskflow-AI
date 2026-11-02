"""Application settings, loaded from environment variables / .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "To-Do API"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Comma separated list of allowed origins
    CORS_ORIGINS: str = "http://localhost:5173"

    # --- Chatbot Assistant (OpenRouter). The key lives only on the server. ---
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = ""  # any OpenRouter model id, e.g. a ":free" model
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_TIMEOUT_SECONDS: float = 45.0
    # auto = try native tool calling, fall back to validated JSON if the model lacks it
    # native = native tool calling only | json = always use the JSON protocol
    OPENROUTER_TOOL_MODE: str = "auto"
    # Optional attribution headers recommended by OpenRouter
    OPENROUTER_SITE_URL: str = ""
    OPENROUTER_APP_NAME: str = "TaskFlow"
    CHATBOT_MAX_HISTORY: int = 10
    CHATBOT_MAX_TOOL_STEPS: int = 5
    CHATBOT_ACTION_TTL_MINUTES: int = 10

    # Optional bootstrap admin
    FIRST_ADMIN_EMAIL: str | None = None
    FIRST_ADMIN_PASSWORD: str | None = None
    FIRST_ADMIN_NAME: str = "System Admin"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def chatbot_enabled(self) -> bool:
        return bool(self.OPENROUTER_API_KEY.strip() and self.OPENROUTER_MODEL.strip())

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
