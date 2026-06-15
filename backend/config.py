from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        str_strip_whitespace=True,
    )

    # YouTube
    youtube_api_key: str = ""

    # Anthropic
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"

    # OpenAI (for Whisper transcription)
    openai_api_key: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///./recipes.db"

    # Instagram (optional - required for fetching posts)
    instagram_username: str = ""
    instagram_password: str = ""

    # Notion (optional - for exporting recipes)
    notion_token: str = ""
    notion_cooking_page_id: str = ""
    notion_auto_sync: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
