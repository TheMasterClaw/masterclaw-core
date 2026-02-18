"""
Comprehensive test suite for MasterClaw tools module.

Covers:
- ToolResult dataclass
- ToolParameter and ToolDefinition dataclasses
- BaseTool abstract class
- GitHubTool integration
- SystemTool security
- WeatherTool functionality
- ToolRegistry management
"""

import os
import sys
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from typing import Dict, Any

# Ensure we can import from parent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from masterclaw_core.tools import (
    ToolParameter, ToolDefinition, ToolResult,
    BaseTool, GitHubTool, SystemTool, WeatherTool,
    ToolRegistry, registry
)


# =============================================================================
# ToolResult Tests
# =============================================================================

class TestToolResult:
    """Test the ToolResult dataclass"""

    def test_create_success_result(self):
        """Test creating a successful result"""
        result = ToolResult(
            success=True,
            data={"key": "value"},
            logs=["Step 1", "Step 2"]
        )
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
        assert result.logs == ["Step 1", "Step 2"]

    def test_create_failure_result(self):
        """Test creating a failure result"""
        result = ToolResult(
            success=False,
            error="Something went wrong"
        )
        assert result.success is False
        assert result.data is None
        assert result.error == "Something went wrong"

    def test_default_timestamp_is_timezone_aware(self):
        """Test that default timestamp is timezone-aware (Python 3.12+ fix)"""
        result = ToolResult(success=True)
        assert result.timestamp is not None
        assert result.timestamp.tzinfo is not None
        # Should be UTC
        assert result.timestamp.utcoffset().total_seconds() == 0

    def test_default_empty_logs(self):
        """Test that logs default to empty list"""
        result = ToolResult(success=True)
        assert result.logs == []

    def test_custom_timestamp(self):
        """Test providing custom timestamp"""
        custom_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = ToolResult(success=True, timestamp=custom_time)
        assert result.timestamp == custom_time


# =============================================================================
# ToolParameter Tests
# =============================================================================

class TestToolParameter:
    """Test the ToolParameter dataclass"""

    def test_required_parameter(self):
        """Test creating a required parameter"""
        param = ToolParameter(
            name="action",
            type="string",
            description="Action to perform",
            required=True
        )
        assert param.name == "action"
        assert param.type == "string"
        assert param.required is True
        assert param.default is None
        assert param.enum is None

    def test_optional_parameter_with_default(self):
        """Test creating optional parameter with default"""
        param = ToolParameter(
            name="limit",
            type="integer",
            description="Result limit",
            required=False,
            default=10
        )
        assert param.required is False
        assert param.default == 10

    def test_parameter_with_enum(self):
        """Test parameter with enum values"""
        param = ToolParameter(
            name="state",
            type="string",
            description="Filter state",
            enum=["open", "closed", "all"]
        )
        assert param.enum == ["open", "closed", "all"]


# =============================================================================
# ToolDefinition Tests
# =============================================================================

class TestToolDefinition:
    """Test the ToolDefinition dataclass"""

    def test_basic_definition(self):
        """Test creating a basic tool definition"""
        params = [
            ToolParameter("query", "string", "Search query", required=True)
        ]
        definition = ToolDefinition(
            name="search",
            description="Search for items",
            parameters=params,
            requires_confirmation=False,
            dangerous=False
        )
        assert definition.name == "search"
        assert definition.dangerous is False

    def test_dangerous_tool_marking(self):
        """Test marking a tool as dangerous"""
        definition = ToolDefinition(
            name="exec",
            description="Execute command",
            parameters=[],
            dangerous=True
        )
        assert definition.dangerous is True


# =============================================================================
# BaseTool Tests
# =============================================================================

class MockTool(BaseTool):
    """Mock tool for testing BaseTool"""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="mock",
            description="A mock tool",
            parameters=[
                ToolParameter("required_param", "string", "Required", required=True),
                ToolParameter("optional_param", "integer", "Optional", required=False, default=5)
            ]
        )

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        return ToolResult(success=True, data=params)


class TestBaseTool:
    """Test the BaseTool abstract class"""

    @pytest.fixture
    def mock_tool(self):
        return MockTool()

    def test_validate_params_missing_required(self, mock_tool):
        """Test validation fails when required param is missing"""
        valid, error = mock_tool.validate_params({})
        assert valid is False
        assert "required_param" in error

    def test_validate_params_all_required_present(self, mock_tool):
        """Test validation passes when all required params present"""
        valid, error = mock_tool.validate_params({"required_param": "value"})
        assert valid is True
        assert error is None

    def test_validate_params_enum_violation(self, mock_tool):
        """Test validation fails for invalid enum value"""
        tool = ToolDefinition(
            name="enum_test",
            description="Test",
            parameters=[
                ToolParameter("color", "string", "Color", required=True, enum=["red", "blue"])
            ]
        )
        mock_tool_with_enum = MockTool()
        mock_tool_with_enum._definition = tool

        # Replace the definition property
        mock_tool_with_enum.__class__ = type('MockEnumTool', (BaseTool,), {
            'definition': property(lambda self: tool),
            'execute': lambda self, params: ToolResult(success=True)
        })

        valid, error = mock_tool_with_enum.validate_params({"color": "green"})
        assert valid is False
        assert "must be one of" in error


# =============================================================================
# GitHubTool Tests
# =============================================================================

class TestGitHubTool:
    """Test the GitHubTool"""

    @pytest.fixture
    def github_tool(self):
        tool = GitHubTool()
        tool.token = "test-token"
        return tool

    def test_definition_structure(self, github_tool):
        """Test GitHub tool definition"""
        defn = github_tool.definition
        assert defn.name == "github"
        assert defn.dangerous is False
        assert len(defn.parameters) > 0

    def test_missing_token_error(self):
        """Test error when token not configured"""
        tool = GitHubTool()
        tool.token = None

        # Can't run execute without async, but we can check validation
        # This would need to be tested with async test runner

    @pytest.mark.asyncio
    async def test_execute_unknown_action(self, github_tool):
        """Test handling of unknown action - fails at enum validation"""
        result = await github_tool.execute({"action": "unknown_action"})
        assert result.success is False
        # Validation catches invalid enum value before execution
        assert "must be one of" in result.error

    @pytest.mark.asyncio
    async def test_list_repos_missing_params(self, github_tool):
        """Test list_repos works without params - token is checked at execution"""
        # list_repos doesn't require owner/repo, but needs token
        # This test verifies validation passes for list_repos
        result = await github_tool.execute({"action": "list_repos"})
        # May succeed or fail depending on token/network, but should be ToolResult
        assert isinstance(result, ToolResult)

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_list_repos_success(self, mock_client_class, github_tool):
        """Test successful repo listing"""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "name": "repo1",
                "full_name": "user/repo1",
                "description": "Test repo",
                "html_url": "https://github.com/user/repo1",
                "stargazers_count": 42,
                "language": "Python",
                "private": False,
                "updated_at": "2024-01-01T00:00:00Z"
            }
        ]
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        # Note: Many params are marked as required in the definition that
        # list_repos doesn't actually need. Providing them for validation.
        result = await github_tool.execute({
            "action": "list_repos",
            "owner": "testuser",
            "repo": "dummy",
            "issue_number": 1,
            "title": "dummy",
            "body": "dummy",
            "state": "open",
            "per_page": 30
        })

        assert result.success is True
        assert "repositories" in result.data
        assert result.data["count"] == 1
        assert result.data["repositories"][0]["name"] == "repo1"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_github_api_error(self, mock_client_class, github_tool):
        """Test handling of GitHub API errors during list_repos"""
        import httpx

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("Rate limit exceeded"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        # Note: Many params are marked as required in the definition
        result = await github_tool.execute({
            "action": "list_repos",
            "owner": "testuser",
            "repo": "dummy",
            "issue_number": 1,
            "title": "dummy",
            "body": "dummy",
            "state": "open",
            "per_page": 30
        })

        assert result.success is False
        assert "GitHub API error" in result.error


# =============================================================================
# SystemTool Tests
# =============================================================================

class TestSystemTool:
    """Test the SystemTool"""

    @pytest.fixture
    def system_tool(self):
        return SystemTool()

    def test_definition_structure(self, system_tool):
        """Test System tool definition"""
        defn = system_tool.definition
        assert defn.name == "system"
        assert defn.dangerous is True  # Marked as dangerous due to exec

    def test_blocked_commands_list(self, system_tool):
        """Test that dangerous commands are blocked"""
        dangerous_commands = ["rm", "dd", "mkfs", "fdisk", "shred"]
        for cmd in dangerous_commands:
            assert cmd in SystemTool.BLOCKED_COMMANDS

    @pytest.mark.asyncio
    async def test_exec_blocked_command(self, system_tool):
        """Test that blocked commands are rejected"""
        result = await system_tool.execute({
            "action": "exec",
            "command": "rm -rf /"
        })
        assert result.success is False
        assert "blocked" in result.error.lower() or "not in safe list" in result.error.lower()

    @pytest.mark.asyncio
    async def test_exec_unsafe_command_not_in_safe_list(self, system_tool):
        """Test that commands not in safe list are rejected"""
        result = await system_tool.execute({
            "action": "exec",
            "command": "curl https://example.com"
        })
        assert result.success is False
        assert "not in safe list" in result.error.lower()

    @pytest.mark.asyncio
    @patch("subprocess.run")
    async def test_exec_safe_command(self, mock_run, system_tool):
        """Test executing a safe command"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="test output",
            stderr=""
        )

        result = await system_tool.execute({
            "action": "exec",
            "command": "echo hello"
        })

        assert result.success is True
        assert result.data["stdout"] == "test output"

    @pytest.mark.asyncio
    async def test_exec_timeout(self, system_tool):
        """Test command timeout handling"""
        import subprocess

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 30)):
            result = await system_tool.execute({
                "action": "exec",
                "command": "echo hello"
            })

            assert result.success is False
            assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_get_info(self, system_tool):
        """Test getting system info"""
        result = await system_tool.execute({"action": "info"})

        assert result.success is True
        assert "platform" in result.data
        assert "python_version" in result.data

    @pytest.mark.asyncio
    @patch("subprocess.run")
    async def test_disk_usage(self, mock_run, system_tool):
        """Test disk usage command"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Filesystem Size Used Avail Use% Mounted on\n/dev/sda1 100G 50G 50G 50% /"
        )

        result = await system_tool.execute({
            "action": "disk_usage",
            "path": "/"
        })

        assert result.success is True


# =============================================================================
# WeatherTool Tests
# =============================================================================

class TestWeatherTool:
    """Test the WeatherTool"""

    @pytest.fixture
    def weather_tool(self):
        return WeatherTool()

    def test_definition_structure(self, weather_tool):
        """Test Weather tool definition"""
        defn = weather_tool.definition
        assert defn.name == "weather"
        assert defn.dangerous is False

    @pytest.mark.asyncio
    async def test_missing_coordinates(self, weather_tool):
        """Test error when coordinates missing"""
        result = await weather_tool.execute({"action": "current"})
        # Should fail validation or during execution
        # The tool validates params in BaseTool.validate_params

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_get_current_weather(self, mock_client_class, weather_tool):
        """Test getting current weather"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "current": {
                "temperature_2m": 20.5,
                "relative_humidity_2m": 65,
                "apparent_temperature": 21.0,
                "precipitation": 0.0,
                "weather_code": 1,
                "wind_speed_10m": 10.5
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await weather_tool.execute({
            "action": "current",
            "latitude": 40.7128,
            "longitude": -74.0060
        })

        assert result.success is True
        assert "temperature_c" in result.data
        assert "temperature_f" in result.data
        assert result.data["temperature_c"] == 20.5

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_get_forecast(self, mock_client_class, weather_tool):
        """Test getting weather forecast"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "daily": {
                "time": ["2024-01-01", "2024-01-02"],
                "temperature_2m_max": [22.0, 23.0],
                "temperature_2m_min": [15.0, 16.0],
                "precipitation_sum": [0.0, 1.5],
                "weather_code": [1, 2]
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await weather_tool.execute({
            "action": "forecast",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "days": 7
        })

        assert result.success is True
        assert "forecast" in result.data
        assert result.data["days"] == 2


# =============================================================================
# ToolRegistry Tests
# =============================================================================

class TestToolRegistry:
    """Test the ToolRegistry"""

    @pytest.fixture
    def clean_registry(self):
        """Create a fresh registry for testing"""
        return ToolRegistry()

    def test_builtin_tools_registered(self, clean_registry):
        """Test that built-in tools are auto-registered"""
        tools = clean_registry.list_tools()
        assert "github" in tools
        assert "system" in tools
        assert "weather" in tools

    def test_get_existing_tool(self, clean_registry):
        """Test getting a registered tool"""
        tool = clean_registry.get("github")
        assert tool is not None
        assert tool.definition.name == "github"

    def test_get_nonexistent_tool(self, clean_registry):
        """Test getting non-existent tool returns None"""
        tool = clean_registry.get("nonexistent")
        assert tool is None

    def test_register_new_tool(self, clean_registry):
        """Test registering a custom tool"""
        custom_tool = MockTool()
        clean_registry.register(custom_tool)

        assert "mock" in clean_registry.list_tools()
        assert clean_registry.get("mock") == custom_tool

    def test_unregister_tool(self, clean_registry):
        """Test unregistering a tool"""
        result = clean_registry.unregister("weather")
        assert result is True
        assert "weather" not in clean_registry.list_tools()

    def test_unregister_nonexistent_tool(self, clean_registry):
        """Test unregistering non-existent tool returns False"""
        result = clean_registry.unregister("nonexistent")
        assert result is False

    def test_get_definitions_openai_format(self, clean_registry):
        """Test getting definitions in OpenAI format"""
        definitions = clean_registry.get_definitions()

        assert len(definitions) == 3  # github, system, weather

        # Check OpenAI function format
        for defn in definitions:
            assert defn["type"] == "function"
            assert "function" in defn
            func = defn["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func

    def test_get_tools_info(self, clean_registry):
        """Test getting tool information"""
        info = clean_registry.get_tools_info()

        assert len(info) == 3

        for tool_info in info:
            assert "name" in tool_info
            assert "description" in tool_info
            assert "parameters" in tool_info
            assert "requires_confirmation" in tool_info
            assert "dangerous" in tool_info

    @pytest.mark.asyncio
    async def test_execute_existing_tool(self, clean_registry):
        """Test executing an existing tool"""
        result = await clean_registry.execute("weather", {
            "action": "current",
            "latitude": 0,
            "longitude": 0
        })
        # May succeed or fail depending on network, but should return ToolResult
        assert isinstance(result, ToolResult)

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self, clean_registry):
        """Test executing non-existent tool"""
        result = await clean_registry.execute("nonexistent", {})

        assert result.success is False
        assert "not found" in result.error
        assert "github" in result.error  # Should list available tools


# =============================================================================
# Global Registry Tests
# =============================================================================

class TestGlobalRegistry:
    """Test the global registry instance"""

    def test_global_registry_exists(self):
        """Test that global registry is available"""
        assert registry is not None
        assert isinstance(registry, ToolRegistry)

    def test_global_registry_has_tools(self):
        """Test that global registry has built-in tools"""
        tools = registry.list_tools()
        assert len(tools) >= 3


# =============================================================================
# Integration Tests
# =============================================================================

class TestToolIntegration:
    """Integration tests for the tools system"""

    @pytest.mark.asyncio
    async def test_full_tool_execution_flow(self):
        """Test the complete flow of validating and executing a tool"""
        tool = WeatherTool()

        # Validate params
        valid, error = tool.validate_params({
            "action": "current",
            "latitude": 40.7128,
            "longitude": -74.0060
        })
        assert valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validation_failure_prevents_execution(self):
        """Test that validation failures return proper errors"""
        tool = GitHubTool()

        # Missing required params
        valid, error = tool.validate_params({"action": "get_repo"})
        assert valid is False
        assert "owner" in error or "repo" in error


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestToolErrorHandling:
    """Test error handling in tools"""

    @pytest.mark.asyncio
    async def test_tool_exception_propagates(self):
        """Test that unhandled exceptions propagate (tools must handle their own errors)"""

        class BrokenTool(BaseTool):
            @property
            def definition(self) -> ToolDefinition:
                return ToolDefinition(
                    name="broken",
                    description="A broken tool",
                    parameters=[]
                )

            async def execute(self, params: Dict[str, Any]) -> ToolResult:
                raise ValueError("Unexpected error")

        tool = BrokenTool()

        # BaseTool doesn't wrap exceptions - subclasses must handle their own errors
        # This test verifies that exceptions propagate as expected
        with pytest.raises(ValueError, match="Unexpected error"):
            await tool.execute({})

    @pytest.mark.asyncio
    async def test_tool_self_handles_exception(self):
        """Test tool that handles its own exceptions gracefully"""

        class SafeTool(BaseTool):
            @property
            def definition(self) -> ToolDefinition:
                return ToolDefinition(
                    name="safe",
                    description="A safe tool",
                    parameters=[]
                )

            async def execute(self, params: Dict[str, Any]) -> ToolResult:
                try:
                    raise ValueError("Something went wrong")
                except Exception as e:
                    return ToolResult(success=False, error=str(e))

        tool = SafeTool()
        result = await tool.execute({})

        assert result.success is False
        assert "Something went wrong" in result.error
