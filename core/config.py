"""Configuration settings for PulseStream."""

import os
from typing import Any, Dict, List, Optional

from pydantic import Field, PostgresDsn, RedisDsn, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = "PulseStream"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # API
    api_v1_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    
    # Security
    secret_key: str = Field(env="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Database
    database_url: PostgresDsn = Field(env="DATABASE_URL")
    database_echo: bool = False
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # Redis
    redis_url: RedisDsn = Field(env="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # Celery
    celery_broker_url: str = Field(env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(env="CELERY_RESULT_BACKEND")
    celery_task_routes: Dict[str, Any] = {
        "apps.processing.tasks.*": {"queue": "processing"},
        "apps.alerting.tasks.*": {"queue": "alerting"},
        "apps.analytics.tasks.*": {"queue": "analytics"},
    }
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 100
    rate_limit_burst: int = 200
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Monitoring
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    
    # Email (for alerting)
    smtp_host: Optional[str] = Field(default=None, env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: Optional[str] = Field(default=None, env="SMTP_USERNAME")
    smtp_password: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    smtp_use_tls: bool = True
    email_from: Optional[str] = Field(default=None, env="EMAIL_FROM")
    
    # Slack (for alerting)
    slack_webhook_url: Optional[str] = Field(default=None, env="SLACK_WEBHOOK_URL")
    
    # OpenAI (for AI analytics - Phase 2)
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    
    @validator("cors_origins", pre=True)
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


class DevelopmentSettings(Settings):
    """Development environment settings."""
    
    debug: bool = True
    reload: bool = True
    database_echo: bool = True
    log_level: str = "DEBUG"
    
    # Default development values
    secret_key: str = "dev-secret-key-change-in-production"
    database_url: PostgresDsn = "postgresql://postgres:postgres@localhost:5432/pulsestream_dev"
    redis_url: RedisDsn = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"


class ProductionSettings(Settings):
    """Production environment settings."""
    
    debug: bool = False
    reload: bool = False
    database_echo: bool = False
    log_level: str = "INFO"


class TestSettings(Settings):
    """Test environment settings."""
    
    debug: bool = True
    database_url: PostgresDsn = "postgresql://postgres:postgres@localhost:5432/pulsestream_test"
    redis_url: RedisDsn = "redis://localhost:6379/15"
    celery_broker_url: str = "redis://localhost:6379/14"
    celery_result_backend: str = "redis://localhost:6379/13"
    
    # Disable external services in tests
    prometheus_enabled: bool = False
    rate_limit_enabled: bool = False


def get_settings() -> Settings:
    """Get settings based on environment."""
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        return ProductionSettings()
    elif environment == "test":
        return TestSettings()
    else:
        return DevelopmentSettings()


# Global settings instance
settings = get_settings()
