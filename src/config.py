"""Configuration for banking support agent."""
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    azure_openai_endpoint: str = Field(default="https://your-openai.openai.azure.com/", env="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(default="your-key", env="AZURE_OPENAI_API_KEY")
    azure_openai_api_version: str = Field(default="2024-02-01", env="AZURE_OPENAI_API_VERSION")
    azure_openai_deployment: str = Field(default="gpt-4o", env="AZURE_OPENAI_DEPLOYMENT")
    content_safety_endpoint: str = Field(default="https://your-content-safety.cognitiveservices.azure.com/", env="CONTENT_SAFETY_ENDPOINT")
    content_safety_key: str = Field(default="your-cs-key", env="CONTENT_SAFETY_KEY")
    keyvault_url: str = Field(default="https://your-keyvault.vault.azure.net/", env="KEYVAULT_URL")
    cosmos_endpoint: str = Field(default="https://your-cosmos.documents.azure.com:443/", env="COSMOS_ENDPOINT")
    cosmos_key: str = Field(default="your-cosmos-key", env="COSMOS_KEY")
    cosmos_database: str = Field(default="banking-support", env="COSMOS_DATABASE")
    cosmos_audit_container: str = Field(default="fca-audit", env="COSMOS_AUDIT_CONTAINER")
    cosmos_sessions_container: str = Field(default="sessions", env="COSMOS_SESSIONS_CONTAINER")
    use_managed_identity: bool = Field(default=False, env="USE_MANAGED_IDENTITY")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
