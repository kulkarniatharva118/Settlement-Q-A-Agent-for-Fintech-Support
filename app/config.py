from __future__ import annotations

import os


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/payment_settlement",
)


def get_llm_config() -> tuple[str | None, str, str | None]:
    """Return runtime LLM settings without logging the API key."""
    return (
        os.getenv("LLM_API_KEY"),
        os.getenv("LLM_MODEL", "openai/gpt-oss-20b:free"),
        os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1"),
    )