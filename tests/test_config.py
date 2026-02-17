"""Tests for configuration validation and security checks"""

import os
import warnings
import pytest
from pydantic import ValidationError
from unittest.mock import patch

from masterclaw_core.config import Settings


class TestPortValidation:
    """Test PORT validation"""
    
    def test_valid_port_low(self):
        """Test minimum valid port"""
        settings = Settings(PORT=1)
        assert settings.PORT == 1
    
    def test_valid_port_high(self):
        """Test maximum valid port"""
        settings = Settings(PORT=65535)
        assert settings.PORT == 65535
    
    def test_valid_port_common(self):
        """Test common ports"""
        for port in [80, 443, 8000, 8080, 3000]:
            settings = Settings(PORT=port)
            assert settings.PORT == port
    
    def test_invalid_port_zero(self):
        """Test port 0 is invalid"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(PORT=0)
        assert "PORT must be between 1 and 65535" in str(exc_info.value)
    
    def test_invalid_port_negative(self):
        """Test negative port is invalid"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(PORT=-1)
        assert "PORT must be between 1 and 65535" in str(exc_info.value)
    
    def test_invalid_port_too_high(self):
        """Test port above 65535 is invalid"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(PORT=65536)
        assert "PORT must be between 1 and 65535" in str(exc_info.value)
    
    def test_invalid_port_way_too_high(self):
        """Test very high port number is invalid"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(PORT=99999)
        assert "PORT must be between 1 and 65535" in str(exc_info.value)


class TestRateLimitValidation:
    """Test RATE_LIMIT_PER_MINUTE validation"""
    
    def test_valid_rate_limit_low(self):
        """Test minimum valid rate limit"""
        settings = Settings(RATE_LIMIT_PER_MINUTE=1)
        assert settings.RATE_LIMIT_PER_MINUTE == 1
    
    def test_valid_rate_limit_default(self):
        """Test default rate limit"""
        settings = Settings()
        assert settings.RATE_LIMIT_PER_MINUTE == 60
    
    def test_valid_rate_limit_high(self):
        """Test high but valid rate limit"""
        settings = Settings(RATE_LIMIT_PER_MINUTE=5000)
        assert settings.RATE_LIMIT_PER_MINUTE == 5000
    
    def test_valid_rate_limit_max(self):
        """Test maximum valid rate limit"""
        settings = Settings(RATE_LIMIT_PER_MINUTE=10000)
        assert settings.RATE_LIMIT_PER_MINUTE == 10000
    
    def test_invalid_rate_limit_zero(self):
        """Test zero rate limit is invalid"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(RATE_LIMIT_PER_MINUTE=0)
        assert "RATE_LIMIT_PER_MINUTE must be at least 1" in str(exc_info.value)
    
    def test_invalid_rate_limit_negative(self):
        """Test negative rate limit is invalid"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(RATE_LIMIT_PER_MINUTE=-10)
        assert "RATE_LIMIT_PER_MINUTE must be at least 1" in str(exc_info.value)
    
    def test_invalid_rate_limit_excessive(self):
        """Test excessively high rate limit is invalid"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(RATE_LIMIT_PER_MINUTE=10001)
        assert "RATE_LIMIT_PER_MINUTE seems excessively high" in str(exc_info.value)


class TestCORSValidation:
    """Test CORS_ORIGINS validation"""
    
    def test_valid_cors_specific_origin(self):
        """Test specific origin is valid"""
        settings = Settings(CORS_ORIGINS=["https://example.com"])
        assert settings.CORS_ORIGINS == ["https://example.com"]
    
    def test_valid_cors_multiple_origins(self):
        """Test multiple origins are valid"""
        origins = ["https://app.example.com", "https://admin.example.com"]
        settings = Settings(CORS_ORIGINS=origins)
        assert settings.CORS_ORIGINS == origins
    
    def test_valid_cors_localhost(self):
        """Test localhost origins are valid"""
        origins = ["http://localhost:3000", "http://localhost:8080"]
        settings = Settings(CORS_ORIGINS=origins)
        assert settings.CORS_ORIGINS == origins
    
    def test_valid_cors_wildcard_development(self):
        """Test wildcard is allowed in development"""
        with patch.dict(os.environ, {}, clear=True):  # Clear env
            settings = Settings(CORS_ORIGINS=["*"])
            assert settings.CORS_ORIGINS == ["*"]
    
    def test_invalid_cors_missing_scheme(self):
        """Test origin without scheme is invalid"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(CORS_ORIGINS=["example.com"])
        assert "must start with http:// or https://" in str(exc_info.value)
    
    def test_invalid_cors_ftp_scheme(self):
        """Test FTP origin is invalid"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(CORS_ORIGINS=["ftp://example.com"])
        assert "must start with http:// or https://" in str(exc_info.value)
    
    def test_invalid_cors_file_scheme(self):
        """Test file:// origin is invalid"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(CORS_ORIGINS=["file:///path"])
        assert "must start with http:// or https://" in str(exc_info.value)
    
    def test_warning_cors_wildcard_production_node_env(self):
        """Test wildcard in production triggers warning (NODE_ENV)"""
        with patch.dict(os.environ, {"NODE_ENV": "production"}):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                Settings(CORS_ORIGINS=["*"])
                
                assert len(w) == 1
                assert issubclass(w[0].category, RuntimeWarning)
                assert "SECURITY WARNING" in str(w[0].message)
                assert "CORS_ORIGINS contains '*' in production" in str(w[0].message)
    
    def test_warning_cors_wildcard_production_env_var(self):
        """Test wildcard in production triggers warning (ENV)"""
        with patch.dict(os.environ, {"ENV": "production"}):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                Settings(CORS_ORIGINS=["*"])
                
                assert len(w) == 1
                assert issubclass(w[0].category, RuntimeWarning)
                assert "SECURITY WARNING" in str(w[0].message)
    
    def test_warning_cors_wildcard_prod_short(self):
        """Test wildcard in prod (short form) triggers warning"""
        with patch.dict(os.environ, {"NODE_ENV": "prod"}):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                Settings(CORS_ORIGINS=["*"])
                
                assert len(w) == 1
                assert issubclass(w[0].category, RuntimeWarning)


class TestSessionTimeoutValidation:
    """Test SESSION_TIMEOUT validation"""
    
    def test_valid_timeout_minimum(self):
        """Test minimum valid timeout (1 minute)"""
        settings = Settings(SESSION_TIMEOUT=60)
        assert settings.SESSION_TIMEOUT == 60
    
    def test_valid_timeout_default(self):
        """Test default timeout (1 hour)"""
        settings = Settings()
        assert settings.SESSION_TIMEOUT == 3600
    
    def test_valid_timeout_one_day(self):
        """Test 24 hour timeout"""
        settings = Settings(SESSION_TIMEOUT=86400)
        assert settings.SESSION_TIMEOUT == 86400
    
    def test_valid_timeout_one_week(self):
        """Test 7 day timeout (maximum allowed)"""
        settings = Settings(SESSION_TIMEOUT=86400 * 7)
        assert settings.SESSION_TIMEOUT == 86400 * 7
    
    def test_invalid_timeout_zero(self):
        """Test zero timeout is invalid"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(SESSION_TIMEOUT=0)
        assert "SESSION_TIMEOUT must be at least 60 seconds" in str(exc_info.value)
    
    def test_invalid_timeout_too_short(self):
        """Test very short timeout is invalid"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(SESSION_TIMEOUT=30)
        assert "SESSION_TIMEOUT must be at least 60 seconds" in str(exc_info.value)
    
    def test_invalid_timeout_excessive(self):
        """Test excessively long timeout is invalid"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(SESSION_TIMEOUT=86400 * 8)  # 8 days
        assert "SESSION_TIMEOUT seems excessively high" in str(exc_info.value)


class TestLogLevelValidation:
    """Test LOG_LEVEL validation"""
    
    def test_valid_log_levels(self):
        """Test all valid log levels"""
        valid_levels = ["debug", "info", "warning", "error", "critical"]
        for level in valid_levels:
            settings = Settings(LOG_LEVEL=level)
            assert settings.LOG_LEVEL == level
    
    def test_valid_log_levels_uppercase(self):
        """Test uppercase log levels are normalized"""
        settings = Settings(LOG_LEVEL="INFO")
        assert settings.LOG_LEVEL == "info"
        
        settings = Settings(LOG_LEVEL="DEBUG")
        assert settings.LOG_LEVEL == "debug"
    
    def test_valid_log_levels_mixed_case(self):
        """Test mixed case log levels are normalized"""
        settings = Settings(LOG_LEVEL="Info")
        assert settings.LOG_LEVEL == "info"
        
        settings = Settings(LOG_LEVEL="WARNING")
        assert settings.LOG_LEVEL == "warning"
    
    def test_invalid_log_level(self):
        """Test invalid log level is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(LOG_LEVEL="verbose")
        assert "LOG_LEVEL must be one of" in str(exc_info.value)
    
    def test_invalid_log_level_typo(self):
        """Test typo in log level is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(LOG_LEVEL="eror")  # typo
        assert "LOG_LEVEL must be one of" in str(exc_info.value)


class TestMemoryBackendValidation:
    """Test MEMORY_BACKEND validation"""
    
    def test_valid_backend_chroma(self):
        """Test chroma backend is valid"""
        settings = Settings(MEMORY_BACKEND="chroma")
        assert settings.MEMORY_BACKEND == "chroma"
    
    def test_valid_backend_json(self):
        """Test json backend is valid"""
        settings = Settings(MEMORY_BACKEND="json")
        assert settings.MEMORY_BACKEND == "json"
    
    def test_valid_backend_uppercase(self):
        """Test uppercase backend is normalized"""
        settings = Settings(MEMORY_BACKEND="CHROMA")
        assert settings.MEMORY_BACKEND == "chroma"
    
    def test_invalid_backend(self):
        """Test invalid backend is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(MEMORY_BACKEND="postgres")
        assert "MEMORY_BACKEND must be one of" in str(exc_info.value)
    
    def test_invalid_backend_empty(self):
        """Test empty backend is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(MEMORY_BACKEND="")
        assert "MEMORY_BACKEND must be one of" in str(exc_info.value)


class TestSecurityReport:
    """Test security report generation"""
    
    def test_security_report_development(self):
        """Test report in development environment"""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            report = settings.get_security_report()
            
            assert report["environment"] == "development"
            assert report["is_production"] is False
            assert report["secure"] is True  # No issues in dev with defaults
            assert len(report["recommendations"]) > 0  # Should have recommendations
    
    def test_security_report_production_secure(self):
        """Test report in production with secure settings"""
        with patch.dict(os.environ, {"NODE_ENV": "production"}):
            settings = Settings(
                CORS_ORIGINS=["https://app.example.com"],
                OPENAI_API_KEY="sk-test123",
                RATE_LIMIT_PER_MINUTE=100
            )
            report = settings.get_security_report()
            
            assert report["environment"] == "production"
            assert report["is_production"] is True
            assert report["secure"] is True
            assert "*" not in report.get("cors_origins", [])
    
    def test_security_report_production_insecure_cors(self):
        """Test report flags insecure CORS in production"""
        with patch.dict(os.environ, {"NODE_ENV": "production"}):
            settings = Settings(CORS_ORIGINS=["*"])
            report = settings.get_security_report()
            
            assert report["is_production"] is True
            assert report["secure"] is False
            assert any("CORS_ORIGINS" in issue for issue in report["issues"])
    
    def test_security_report_missing_api_keys(self):
        """Test report flags missing API keys as config issues (not security issues)"""
        settings = Settings(OPENAI_API_KEY=None, ANTHROPIC_API_KEY=None)
        report = settings.get_security_report()
        
        # API key issues are now config_issues, not security issues
        assert any("API keys" in issue for issue in report["config_issues"])
        assert report["has_openai_key"] is False
        assert report["has_anthropic_key"] is False
        # Missing API keys shouldn't make the config "insecure" - they're functionality issues
        assert "secure" in report
    
    def test_security_report_high_rate_limit(self):
        """Test report recommends against very high rate limit"""
        settings = Settings(RATE_LIMIT_PER_MINUTE=5000)
        report = settings.get_security_report()
        
        assert any("very high" in rec for rec in report["recommendations"])
    
    def test_security_report_low_rate_limit(self):
        """Test report recommends against very low rate limit"""
        settings = Settings(RATE_LIMIT_PER_MINUTE=5)
        report = settings.get_security_report()
        
        assert any("very low" in rec for rec in report["recommendations"])
    
    def test_security_report_long_session(self):
        """Test report recommends against long sessions"""
        settings = Settings(SESSION_TIMEOUT=86400 * 2)  # 2 days
        report = settings.get_security_report()
        
        assert any("24 hours" in rec for rec in report["recommendations"])
    
    def test_security_report_config_issues_separate_from_security(self):
        """Test that config_issues don't affect 'secure' flag"""
        settings = Settings(
            OPENAI_API_KEY=None,
            ANTHROPIC_API_KEY=None,
            CORS_ORIGINS=["https://example.com"]
        )
        report = settings.get_security_report()
        
        # Should have config issues but still be "secure"
        assert len(report["config_issues"]) > 0
        assert report["secure"] is True
        assert len(report["issues"]) == 0


class TestMultipleValidationErrors:
    """Test multiple validation errors at once"""
    
    def test_multiple_invalid_settings(self):
        """Test that multiple invalid settings all raise errors"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                PORT=99999,
                RATE_LIMIT_PER_MINUTE=-1,
                SESSION_TIMEOUT=5,
                LOG_LEVEL="invalid"
            )
        
        error_str = str(exc_info.value)
        assert "PORT must be between" in error_str
        assert "RATE_LIMIT_PER_MINUTE must be at least" in error_str
        assert "SESSION_TIMEOUT must be at least" in error_str
        assert "LOG_LEVEL must be one of" in error_str


class TestEnvironmentVariableOverride:
    """Test that environment variables properly override defaults"""
    
    def test_env_var_port(self):
        """Test PORT can be set via environment"""
        with patch.dict(os.environ, {"PORT": "9000"}):
            settings = Settings()
            assert settings.PORT == 9000
    
    def test_env_var_cors_origins(self):
        """Test CORS_ORIGINS can be set via environment"""
        # Pydantic handles list parsing from env
        with patch.dict(os.environ, {"CORS_ORIGINS": '["https://app.example.com"]'}):
            settings = Settings()
            assert settings.CORS_ORIGINS == ["https://app.example.com"]
    
    def test_env_var_rate_limit(self):
        """Test RATE_LIMIT_PER_MINUTE can be set via environment"""
        with patch.dict(os.environ, {"RATE_LIMIT_PER_MINUTE": "120"}):
            settings = Settings()
            assert settings.RATE_LIMIT_PER_MINUTE == 120
    
    def test_env_var_invalid_port(self):
        """Test invalid PORT from environment is rejected"""
        with patch.dict(os.environ, {"PORT": "abc"}):
            with pytest.raises(ValidationError):
                Settings()


class TestDefaultValues:
    """Test that default values are reasonable"""
    
    def test_default_port(self):
        """Test default port is 8000"""
        settings = Settings()
        assert settings.PORT == 8000
    
    def test_default_host(self):
        """Test default host is 0.0.0.0"""
        settings = Settings()
        assert settings.HOST == "0.0.0.0"
    
    def test_default_cors_origins(self):
        """Test default CORS is permissive (for development)"""
        settings = Settings()
        assert settings.CORS_ORIGINS == ["*"]
    
    def test_default_rate_limit(self):
        """Test default rate limit is 60/minute"""
        settings = Settings()
        assert settings.RATE_LIMIT_PER_MINUTE == 60
    
    def test_default_session_timeout(self):
        """Test default session timeout is 1 hour"""
        settings = Settings()
        assert settings.SESSION_TIMEOUT == 3600
    
    def test_default_log_level(self):
        """Test default log level is info"""
        settings = Settings()
        assert settings.LOG_LEVEL == "info"
    
    def test_default_memory_backend(self):
        """Test default memory backend is chroma"""
        settings = Settings()
        assert settings.MEMORY_BACKEND == "chroma"
    
    def test_default_model(self):
        """Test default model is gpt-4"""
        settings = Settings()
        assert settings.DEFAULT_MODEL == "gpt-4"
    
    def test_default_provider(self):
        """Test default provider is openai"""
        settings = Settings()
        assert settings.DEFAULT_PROVIDER == "openai"
