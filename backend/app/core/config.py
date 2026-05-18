from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    MONGODB_URI: str = "mongodb://mongodb:27017"
    MONGODB_DB_NAME: str = "rag_chatbot"
    CHROMA_PERSIST_DIR: str = "./chroma"
    CHROMA_COLLECTION_NAME: str = "rag_chunks"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    UPLOAD_DIR: str = "./storage/raw"
    MARKDOWN_DIR: str = "./storage/markdown"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    @property
    def cors_origins(self) -> list[str]:
        return self.CORS_ORIGINS

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
