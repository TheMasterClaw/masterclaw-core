"""Configuration management for MasterClaw Core"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    LOG_LEVEL: str = "info"
    
    # LLM Configuration
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    DEFAULT_MODEL: str = "gpt-4"
    DEFAULT_PROVIDER: str = "openai"
    
    # Memory Configuration
    MEMORY_BACKEND: str = "chroma"  # chroma, json
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    # Session Configuration
    SESSION_TIMEOUT: int = 3600  # 1 hour
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
