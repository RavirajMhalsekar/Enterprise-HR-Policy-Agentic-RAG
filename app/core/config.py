from typing import Any
from pydantic import Field, AliasChoices, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


def _strip_quotes(value: Any) -> Any:
    if isinstance(value, str):
        cleaned = value.strip()
        if (cleaned.startswith('"') and cleaned.endswith('"')) or (
            cleaned.startswith("'") and cleaned.endswith("'")
        ):
            cleaned = cleaned[1:-1].strip()
        return cleaned
    return value


class Settings(BaseSettings):
    app_name: str = "Enterprise HR Policy Agentic RAG Copilot"
    app_env: str = "development"
    google_api_key: str = ""
    tavily_api_key: str = ""
    pinecone_api_key: str = ""
    pinecone_index_name: str = "enterprise-hr-policy-agentic-rag"
    pinecone_namespace: str = "company-hr-kb"
    embedding_model: str = "gemini-embedding-2"
    google_model: str = Field(
        default="gemini-2.5-flash",
        validation_alias=AliasChoices(
            "google_model", "default_model", "openai_model",
            "GOOGLE_MODEL", "DEFAULT_MODEL", "OPENAI_MODEL"
        ),
    )
    top_k: int = 4
    max_retries: int = 2
    admin_api_key: str = ""
    audit_db_path: str = str(BASE_DIR / "data" / "audit.db")
    upload_dir: str = str(BASE_DIR / "uploads")
    sample_kb_dir: str = str(BASE_DIR / "data" / "sample_kb")

    # Authentication & Security (loaded from environment variables, no hardcoded secrets)
    jwt_secret_key: str = Field(
        default="",
        validation_alias=AliasChoices("jwt_secret_key", "JWT_SECRET_KEY"),
    )
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 120
    jwt_cookie_name: str = "access_token"

    demo_user_username: str = Field(
        default="",
        validation_alias=AliasChoices("demo_user_username", "DEMO_USER_USERNAME"),
    )
    demo_user_password: str = Field(
        default="",
        validation_alias=AliasChoices("demo_user_password", "DEMO_USER_PASSWORD"),
    )
    demo_admin_username: str = Field(
        default="",
        validation_alias=AliasChoices("demo_admin_username", "DEMO_ADMIN_USERNAME"),
    )
    demo_admin_password: str = Field(
        default="",
        validation_alias=AliasChoices("demo_admin_password", "DEMO_ADMIN_PASSWORD"),
    )

    # Rate Limiting (per-user in-memory)
    chat_rate_limit: int = 20  # max 20 requests per hour for non-admin
    chat_rate_window_seconds: int = 3600  # 1 hour
    ingest_rate_limit: int = 5  # max 5 requests per minute for admin
    ingest_rate_window_seconds: int = 60  # 1 minute

    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), extra="ignore")

    @field_validator(
        "google_api_key",
        "tavily_api_key",
        "pinecone_api_key",
        "pinecone_index_name",
        "pinecone_namespace",
        "embedding_model",
        "google_model",
        "jwt_secret_key",
        "demo_user_username",
        "demo_user_password",
        "demo_admin_username",
        "demo_admin_password",
        mode="before",
    )
    @classmethod
    def clean_string_fields(cls, v: Any) -> Any:
        return _strip_quotes(v)

    @property
    def openai_model(self) -> str:
        return self.google_model

    @property
    def default_model(self) -> str:
        return self.google_model


@lru_cache
def get_settings() -> Settings:
    return Settings()

