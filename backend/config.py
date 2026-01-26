from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
