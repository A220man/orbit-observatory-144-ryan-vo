from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "Orbit Observatory"
    app_version: str = "1.0.0"
    debug: bool = False

    database_url: str = "sqlite+aiosqlite:///./orbit.db"

    # Keycloak/OIDC
    oidc_issuer_url: str = "http://localhost:8080/realms/orbit"
    oidc_client_id: str = "orbit-observatory"
    oidc_client_secret: str = ""
    oidc_redirect_uri: str = "http://localhost:3000/callback"

    # LLM (opt-in, advisory only)
    llm_api_key: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_base_url: Optional[str] = None

    # Compression settings
    compress_model_context_limit: int = 100000
    compress_max_context_limit: str = "60%"
    compress_nudge_growth_tokens: int = 50000
    compress_reasoning_drop: bool = False
    dsh_allow_dsh_compaction: bool = False
    trae_compact_enabled: bool = True

    # Diagnostics
    diagnostics_log_retention_days: int = 7
    diagnostics_max_total_bytes: int = 100_000_000

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()