"""
Configuration management for the personal assistant.
Loads settings from environment variables and provides typed configuration.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # LLM Configuration
    llm_provider: str = Field(default="ollama", env="LLM_PROVIDER")
    llm_model: str = Field(default="llama3.1:8b", env="LLM_MODEL")

    # OpenAI
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-turbo-preview", env="OPENAI_MODEL")

    # Anthropic
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-5-sonnet-20241022", env="ANTHROPIC_MODEL")

    # Groq
    groq_api_key: Optional[str] = Field(default=None, env="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.1-70b-versatile", env="GROQ_MODEL")

    # Ollama
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")

    # Google Calendar
    google_credentials_path: str = Field(default="config/google_credentials.json", env="GOOGLE_CREDENTIALS_PATH")
    google_token_path: str = Field(default="config/google_token.json", env="GOOGLE_TOKEN_PATH")

    # Notion
    notion_api_key: Optional[str] = Field(default=None, env="NOTION_API_KEY")
    notion_database_id: Optional[str] = Field(default=None, env="NOTION_DATABASE_ID")

    # Email Configuration
    email_imap_server: str = Field(default="imap.gmail.com", env="EMAIL_IMAP_SERVER")
    email_address: Optional[str] = Field(default=None, env="EMAIL_ADDRESS")
    email_password: Optional[str] = Field(default=None, env="EMAIL_PASSWORD")

    # Database
    database_url: str = Field(default="sqlite:///data/assistant.db", env="DATABASE_URL")

    # Server Configuration
    server_host: str = Field(default="0.0.0.0", env="SERVER_HOST")
    server_port: int = Field(default=8000, env="SERVER_PORT")

    # Scheduling
    daily_briefing_time: str = Field(default="08:00", env="DAILY_BRIEFING_TIME")
    evening_summary_time: str = Field(default="20:00", env="EVENING_SUMMARY_TIME")

    # Notifications
    notification_email: Optional[str] = Field(default=None, env="NOTIFICATION_EMAIL")
    enable_terminal_notifications: bool = Field(default=True, env="ENABLE_TERMINAL_NOTIFICATIONS")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="data/assistant.log", env="LOG_FILE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def get_llm_config(self):
        """Get LLM configuration based on selected provider"""
        provider = self.llm_provider.lower()

        if provider == "ollama":
            return {
                "provider": provider,
                "model": self.llm_model,
                "base_url": self.ollama_base_url,
            }
        elif provider == "openai":
            return {
                "provider": provider,
                "model": self.openai_model,
                "api_key": self.openai_api_key,
            }
        elif provider == "anthropic":
            return {
                "provider": provider,
                "model": self.anthropic_model,
                "api_key": self.anthropic_api_key,
            }
        elif provider == "groq":
            return {
                "provider": provider,
                "model": self.groq_model,
                "api_key": self.groq_api_key,
            }
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance"""
    return settings
