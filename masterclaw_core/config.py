"""Configuration management for MasterClaw Core"""

import os
import warnings
from typing import Optional, Any
from pydantic_settings import BaseSettings
from pydantic import field_validator, ValidationInfo


class Settings(BaseSettings):
    """Application settings with security validation"""
    
    # API Configuration
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    LOG_LEVEL: str = "info"
    
    # Security Configuration
    RATE_LIMIT_PER_MINUTE: int = 60
    CORS_ORIGINS: list[str] = ["*"]  # Configure for production
    
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
    
    @field_validator("PORT")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port is in valid range"""
        if not 1 <= v <= 65535:
            raise ValueError(f"PORT must be between 1 and 65535, got {v}")
        return v
    
    @field_validator("RATE_LIMIT_PER_MINUTE")
    @classmethod
    def validate_rate_limit(cls, v: int) -> int:
        """Validate rate limit is reasonable"""
        if v < 1:
            raise ValueError(f"RATE_LIMIT_PER_MINUTE must be at least 1, got {v}")
        if v > 10000:
            raise ValueError(f"RATE_LIMIT_PER_MINUTE seems excessively high: {v}")
        return v
    
    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, v: list[str], info: ValidationInfo) -> list[str]:
        """Warn about insecure CORS configuration in production"""
        # Check if we're in production mode
        env = os.getenv("NODE_ENV", os.getenv("ENV", "development")).lower()
        is_production = env in ("production", "prod")
        
        if is_production and "*" in v:
            warnings.warn(
                "SECURITY WARNING: CORS_ORIGINS contains '*' in production environment. "
                "This allows any website to make requests to your API. "
                "Consider setting specific origins like ['https://yourdomain.com']",
                RuntimeWarning,
                stacklevel=2
            )
        
        # Validate each origin format
        for origin in v:
            if origin == "*":
                continue
            # Basic URL validation
            if not origin.startswith(("http://", "https://")):
                raise ValueError(
                    f"CORS origin '{origin}' must start with http:// or https://"
                )
        
        return v
    
    @field_validator("SESSION_TIMEOUT")
    @classmethod
    def validate_session_timeout(cls, v: int) -> int:
        """Validate session timeout is reasonable"""
        if v < 60:
            raise ValueError(f"SESSION_TIMEOUT must be at least 60 seconds (1 minute), got {v}")
        if v > 86400 * 7:  # 7 days
            raise ValueError(f"SESSION_TIMEOUT seems excessively high: {v} seconds (>{v/86400:.1f} days)")
        return v
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the standard levels"""
        valid_levels = ("debug", "info", "warning", "error", "critical")
        v_lower = v.lower()
        if v_lower not in valid_levels:
            raise ValueError(
                f"LOG_LEVEL must be one of {valid_levels}, got '{v}'"
            )
        return v_lower
    
    @field_validator("MEMORY_BACKEND")
    @classmethod
    def validate_memory_backend(cls, v: str) -> str:
        """Validate memory backend is supported"""
        valid_backends = ("chroma", "json")
        v_lower = v.lower()
        if v_lower not in valid_backends:
            raise ValueError(
                f"MEMORY_BACKEND must be one of {valid_backends}, got '{v}'"
            )
        return v_lower
    
    def get_security_report(self) -> dict[str, Any]:
        """
        Generate a security configuration report.
        
        Distinguishes between security issues (vulnerabilities) and 
        configuration issues (functionality problems).
        
        Returns:
            Dict containing:
            - environment: Current environment name
            - is_production: Whether running in production
            - secure: True if no security vulnerabilities detected
            - issues: Security vulnerability issues
            - config_issues: Non-security configuration problems
            - recommendations: Security improvement suggestions
        """
        env = os.getenv("NODE_ENV", os.getenv("ENV", "development")).lower()
        is_production = env in ("production", "prod")
        
        issues = []  # Security vulnerabilities
        config_issues = []  # Configuration/functionality problems
        recommendations = []  # Security improvement suggestions
        
        # Check CORS - This IS a security issue in production
        if "*" in self.CORS_ORIGINS:
            if is_production:
                issues.append("CORS_ORIGINS allows all origins (*) in production")
            recommendations.append("Set specific CORS origins instead of '*' for better security")
        
        # Check API keys - This is a config issue, NOT a security issue
        # Missing keys don't create vulnerabilities, they just break functionality
        if not self.OPENAI_API_KEY and not self.ANTHROPIC_API_KEY:
            config_issues.append("No LLM API keys configured - chat functionality will fail")
        
        # Check rate limiting - Only flag as security issue if extremely permissive
        # Note: Values >10000 are rejected by validator, so we only check validated values
        if self.RATE_LIMIT_PER_MINUTE > 1000:
            recommendations.append("RATE_LIMIT_PER_MINUTE is very high (>1000), consider lowering")
        elif self.RATE_LIMIT_PER_MINUTE < 10:
            recommendations.append("RATE_LIMIT_PER_MINUTE is very low (<10), may impact usability")
        
        # Check session timeout - Flag if excessively long (security risk)
        # Note: Values >7 days are rejected by validator
        if self.SESSION_TIMEOUT > 86400:  # 24 hours
            recommendations.append("SESSION_TIMEOUT exceeds 24 hours, consider shorter sessions")
        
        # Production-specific security checks
        if is_production:
            # Check for default/weak settings that are risky in production
            if self.RATE_LIMIT_PER_MINUTE > 1000:
                issues.append(f"RATE_LIMIT_PER_MINUTE ({self.RATE_LIMIT_PER_MINUTE}) is too high for production")
        
        return {
            "environment": env,
            "is_production": is_production,
            "secure": len(issues) == 0,
            "issues": issues,
            "config_issues": config_issues,
            "recommendations": recommendations,
            "cors_origins_count": len(self.CORS_ORIGINS),
            "rate_limit": self.RATE_LIMIT_PER_MINUTE,
            "has_openai_key": bool(self.OPENAI_API_KEY),
            "has_anthropic_key": bool(self.ANTHROPIC_API_KEY),
        }
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
