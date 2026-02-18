"""
MasterClaw Tool Use Framework

Provides a flexible, secure tool calling system for AI agents.
Built-in tools include GitHub integration, system commands, and more.
"""

import os
import json
import subprocess
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable, AsyncGenerator
from datetime import datetime, timezone
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger("masterclaw.tools")


@dataclass
class ToolParameter:
    """Definition of a tool parameter"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None


@dataclass
class ToolDefinition:
    """Complete definition of a tool for LLM tool calling"""
    name: str
    description: str
    parameters: List[ToolParameter]
    requires_confirmation: bool = False
    dangerous: bool = False  # Requires extra security checks


@dataclass
class ToolResult:
    """Result of a tool execution"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BaseTool(ABC):
    """Abstract base class for all tools"""
    
    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Return the tool definition for LLM consumption"""
        pass
    
    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Execute the tool with given parameters"""
        pass
    
    def validate_params(self, params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate parameters against tool definition"""
        definition = self.definition
        
        for param in definition.parameters:
            if param.required and param.name not in params:
                return False, f"Required parameter '{param.name}' is missing"
            
            if param.name in params and param.enum:
                if params[param.name] not in param.enum:
                    return False, f"Parameter '{param.name}' must be one of: {param.enum}"
        
        return True, None


class GitHubTool(BaseTool):
    """
    GitHub API integration tool.
    
    Supports common operations like listing repos, issues, PRs,
    and creating comments.
    """
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="github",
            description="Interact with GitHub repositories, issues, and pull requests",
            parameters=[
                ToolParameter("action", "string", "Action to perform", required=True, 
                             enum=["list_repos", "get_repo", "list_issues", "get_issue", 
                                   "create_issue", "list_prs", "get_pr", "create_comment"]),
                ToolParameter("owner", "string", "Repository owner (username or org)"),
                ToolParameter("repo", "string", "Repository name"),
                ToolParameter("issue_number", "integer", "Issue or PR number"),
                ToolParameter("title", "string", "Title for new issue"),
                ToolParameter("body", "string", "Body content for issue/comment"),
                ToolParameter("state", "string", "Filter by state", default="open",
                             enum=["open", "closed", "all"]),
                ToolParameter("per_page", "integer", "Results per page", default=30),
            ],
            requires_confirmation=False,
            dangerous=False
        )
    
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        valid, error = self.validate_params(params)
        if not valid:
            return ToolResult(success=False, error=error)
        
        if not self.token:
            return ToolResult(success=False, error="GITHUB_TOKEN not configured")
        
        action = params.get("action")
        
        try:
            if action == "list_repos":
                return await self._list_repos(params)
            elif action == "get_repo":
                return await self._get_repo(params)
            elif action == "list_issues":
                return await self._list_issues(params)
            elif action == "get_issue":
                return await self._get_issue(params)
            elif action == "create_issue":
                return await self._create_issue(params)
            elif action == "list_prs":
                return await self._list_prs(params)
            elif action == "get_pr":
                return await self._get_pr(params)
            elif action == "create_comment":
                return await self._create_comment(params)
            else:
                return ToolResult(success=False, error=f"Unknown action: {action}")
        
        except httpx.HTTPError as e:
            return ToolResult(success=False, error=f"GitHub API error: {str(e)}")
        except Exception as e:
            logger.error(f"GitHub tool error: {e}")
            return ToolResult(success=False, error=f"Unexpected error: {str(e)}")
    
    async def _list_repos(self, params: Dict[str, Any]) -> ToolResult:
        """List repositories for authenticated user"""
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/user/repos",
                headers=headers,
                params={"per_page": params.get("per_page", 30)}
            )
            resp.raise_for_status()
            data = resp.json()
        
        repos = [
            {
                "name": r["name"],
                "full_name": r["full_name"],
                "description": r.get("description"),
                "url": r["html_url"],
                "stars": r["stargazers_count"],
                "language": r.get("language"),
                "private": r["private"],
                "updated_at": r["updated_at"],
            }
            for r in data
        ]
        
        return ToolResult(success=True, data={"repositories": repos, "count": len(repos)})
    
    async def _get_repo(self, params: Dict[str, Any]) -> ToolResult:
        """Get details for a specific repository"""
        owner = params.get("owner")
        repo = params.get("repo")
        
        if not owner or not repo:
            return ToolResult(success=False, error="owner and repo are required")
        
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}",
                headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
        
        return ToolResult(success=True, data={
            "name": data["name"],
            "full_name": data["full_name"],
            "description": data.get("description"),
            "url": data["html_url"],
            "stars": data["stargazers_count"],
            "forks": data["forks_count"],
            "open_issues": data["open_issues_count"],
            "language": data.get("language"),
            "default_branch": data["default_branch"],
            "created_at": data["created_at"],
            "updated_at": data["updated_at"],
        })
    
    async def _list_issues(self, params: Dict[str, Any]) -> ToolResult:
        """List issues for a repository"""
        owner = params.get("owner")
        repo = params.get("repo")
        
        if not owner or not repo:
            return ToolResult(success=False, error="owner and repo are required")
        
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/issues",
                headers=headers,
                params={
                    "state": params.get("state", "open"),
                    "per_page": params.get("per_page", 30)
                }
            )
            resp.raise_for_status()
            data = resp.json()
        
        issues = [
            {
                "number": i["number"],
                "title": i["title"],
                "state": i["state"],
                "url": i["html_url"],
                "created_at": i["created_at"],
                "updated_at": i["updated_at"],
                "author": i["user"]["login"],
                "labels": [l["name"] for l in i.get("labels", [])],
            }
            for i in data if "pull_request" not in i  # Exclude PRs
        ]
        
        return ToolResult(success=True, data={"issues": issues, "count": len(issues)})
    
    async def _get_issue(self, params: Dict[str, Any]) -> ToolResult:
        """Get a specific issue"""
        owner = params.get("owner")
        repo = params.get("repo")
        issue_number = params.get("issue_number")
        
        if not all([owner, repo, issue_number]):
            return ToolResult(success=False, error="owner, repo, and issue_number are required")
        
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}",
                headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
        
        return ToolResult(success=True, data={
            "number": data["number"],
            "title": data["title"],
            "body": data.get("body", ""),
            "state": data["state"],
            "url": data["html_url"],
            "created_at": data["created_at"],
            "updated_at": data["updated_at"],
            "author": data["user"]["login"],
            "labels": [l["name"] for l in data.get("labels", [])],
            "comments": data["comments"],
        })
    
    async def _create_issue(self, params: Dict[str, Any]) -> ToolResult:
        """Create a new issue (requires confirmation)"""
        owner = params.get("owner")
        repo = params.get("repo")
        title = params.get("title")
        body = params.get("body", "")
        
        if not all([owner, repo, title]):
            return ToolResult(success=False, error="owner, repo, and title are required")
        
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/repos/{owner}/{repo}/issues",
                headers=headers,
                json={"title": title, "body": body}
            )
            resp.raise_for_status()
            data = resp.json()
        
        return ToolResult(success=True, data={
            "number": data["number"],
            "title": data["title"],
            "url": data["html_url"],
            "state": data["state"],
            "created_at": data["created_at"],
        })
    
    async def _list_prs(self, params: Dict[str, Any]) -> ToolResult:
        """List pull requests"""
        owner = params.get("owner")
        repo = params.get("repo")
        
        if not owner or not repo:
            return ToolResult(success=False, error="owner and repo are required")
        
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/pulls",
                headers=headers,
                params={
                    "state": params.get("state", "open"),
                    "per_page": params.get("per_page", 30)
                }
            )
            resp.raise_for_status()
            data = resp.json()
        
        prs = [
            {
                "number": p["number"],
                "title": p["title"],
                "state": p["state"],
                "url": p["html_url"],
                "created_at": p["created_at"],
                "updated_at": p["updated_at"],
                "author": p["user"]["login"],
                "branch": p["head"]["ref"],
                "draft": p["draft"],
            }
            for p in data
        ]
        
        return ToolResult(success=True, data={"pull_requests": prs, "count": len(prs)})
    
    async def _get_pr(self, params: Dict[str, Any]) -> ToolResult:
        """Get a specific pull request"""
        owner = params.get("owner")
        repo = params.get("repo")
        pr_number = params.get("issue_number")
        
        if not all([owner, repo, pr_number]):
            return ToolResult(success=False, error="owner, repo, and issue_number are required")
        
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}",
                headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
        
        return ToolResult(success=True, data={
            "number": data["number"],
            "title": data["title"],
            "body": data.get("body", ""),
            "state": data["state"],
            "url": data["html_url"],
            "created_at": data["created_at"],
            "updated_at": data["updated_at"],
            "author": data["user"]["login"],
            "branch": data["head"]["ref"],
            "base_branch": data["base"]["ref"],
            "draft": data["draft"],
            "merged": data["merged"],
            "mergeable": data.get("mergeable"),
            "additions": data.get("additions"),
            "deletions": data.get("deletions"),
            "changed_files": data.get("changed_files"),
        })
    
    async def _create_comment(self, params: Dict[str, Any]) -> ToolResult:
        """Create a comment on an issue or PR"""
        owner = params.get("owner")
        repo = params.get("repo")
        issue_number = params.get("issue_number")
        body = params.get("body", "")
        
        if not all([owner, repo, issue_number, body]):
            return ToolResult(success=False, error="owner, repo, issue_number, and body are required")
        
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments",
                headers=headers,
                json={"body": body}
            )
            resp.raise_for_status()
            data = resp.json()
        
        return ToolResult(success=True, data={
            "id": data["id"],
            "url": data["html_url"],
            "created_at": data["created_at"],
        })


class SystemTool(BaseTool):
    """
    System information and command execution tool.
    
    Provides safe access to system information and controlled
    command execution with security restrictions.
    """
    
    # Commands that are never allowed
    BLOCKED_COMMANDS = [
        "rm", "dd", "mkfs", "fdisk", "format", "del", "erase",
        "shred", "wipe", ">:", ">", "|", ";", "&&", "||", "`", "$"
    ]
    
    # Safe commands that can be executed without confirmation
    SAFE_COMMANDS = [
        "ls", "cat", "head", "tail", "grep", "find", "pwd", "whoami",
        "date", "uname", "df", "du", "ps", "top", "htop", "free",
        "uptime", "echo", "which", "git status", "git log", "git diff",
        "git branch", "git remote", "docker ps", "docker images",
        "npm list", "pip list", "python --version", "node --version"
    ]
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="system",
            description="Execute safe system commands and get system information",
            parameters=[
                ToolParameter("action", "string", "Action to perform", required=True,
                             enum=["info", "exec", "disk_usage", "memory", "processes"]),
                ToolParameter("command", "string", "Command to execute (for exec action)", required=False),
                ToolParameter("path", "string", "Path for disk_usage action", required=False, default="."),
            ],
            requires_confirmation=False,
            dangerous=True  # Marked dangerous due to exec capability
        )
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        valid, error = self.validate_params(params)
        if not valid:
            return ToolResult(success=False, error=error)
        
        action = params.get("action")
        
        try:
            if action == "info":
                return await self._get_info()
            elif action == "exec":
                return await self._exec_command(params.get("command", ""))
            elif action == "disk_usage":
                return await self._disk_usage(params.get("path", "."))
            elif action == "memory":
                return await self._memory_info()
            elif action == "processes":
                return await self._processes()
            else:
                return ToolResult(success=False, error=f"Unknown action: {action}")
        
        except Exception as e:
            logger.error(f"System tool error: {e}")
            return ToolResult(success=False, error=f"Error: {str(e)}")
    
    async def _get_info(self) -> ToolResult:
        """Get basic system information"""
        import platform
        
        data = {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
        }
        
        return ToolResult(success=True, data=data)
    
    async def _exec_command(self, command: str) -> ToolResult:
        """Execute a command with security checks"""
        if not command:
            return ToolResult(success=False, error="Command is required")
        
        # Security checks
        cmd_lower = command.lower().strip()
        
        # Check for blocked commands
        for blocked in self.BLOCKED_COMMANDS:
            if blocked in cmd_lower:
                return ToolResult(
                    success=False, 
                    error=f"Command contains blocked keyword: {blocked}"
                )
        
        # Check if command is in safe list
        is_safe = any(cmd_lower.startswith(safe) for safe in self.SAFE_COMMANDS)
        
        if not is_safe:
            logger.warning(f"Potentially unsafe command blocked: {command}")
            return ToolResult(
                success=False,
                error=f"Command not in safe list. Allowed: {', '.join(self.SAFE_COMMANDS[:10])}..."
            )
        
        try:
            # Execute with timeout
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.getcwd()
            )
            
            return ToolResult(
                success=result.returncode == 0,
                data={
                    "stdout": result.stdout[:10000],  # Limit output
                    "stderr": result.stderr[:5000] if result.stderr else None,
                    "returncode": result.returncode,
                },
                logs=[f"Executed: {command}"]
            )
        
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error="Command timed out after 30 seconds")
        except Exception as e:
            return ToolResult(success=False, error=f"Execution failed: {str(e)}")
    
    async def _disk_usage(self, path: str) -> ToolResult:
        """Get disk usage for a path"""
        try:
            result = subprocess.run(
                ["df", "-h", path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                headers = lines[0].split()
                values = lines[1].split()
                data = dict(zip(headers, values))
            else:
                data = {"raw": result.stdout}
            
            return ToolResult(success=True, data=data)
        
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    async def _memory_info(self) -> ToolResult:
        """Get memory information"""
        try:
            result = subprocess.run(
                ["free", "-h"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            lines = result.stdout.strip().split("\n")
            data = {"raw": result.stdout}
            
            # Parse the output
            if len(lines) >= 2:
                mem_line = lines[1].split()
                if len(mem_line) >= 4:
                    data["memory"] = {
                        "total": mem_line[1],
                        "used": mem_line[2],
                        "free": mem_line[3],
                    }
            
            return ToolResult(success=True, data=data)
        
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    async def _processes(self) -> ToolResult:
        """Get top processes by CPU"""
        try:
            result = subprocess.run(
                ["ps", "aux", "--sort=-%cpu"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            lines = result.stdout.strip().split("\n")
            # Header + top 10 processes
            top_processes = []
            for line in lines[1:11]:  # Skip header, take top 10
                parts = line.split()
                if len(parts) >= 11:
                    top_processes.append({
                        "user": parts[0],
                        "pid": parts[1],
                        "cpu": parts[2],
                        "mem": parts[3],
                        "command": " ".join(parts[10:])[:50]
                    })
            
            return ToolResult(success=True, data={"processes": top_processes})
        
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class WeatherTool(BaseTool):
    """
    Weather information tool using Open-Meteo API.
    
    Provides current weather and forecasts without requiring API keys.
    """
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="weather",
            description="Get current weather and forecasts for a location",
            parameters=[
                ToolParameter("action", "string", "Action to perform", required=True,
                             enum=["current", "forecast"]),
                ToolParameter("latitude", "float", "Latitude", required=True),
                ToolParameter("longitude", "float", "Longitude", required=True),
                ToolParameter("days", "integer", "Forecast days (1-14)", required=False, default=7),
            ],
            requires_confirmation=False,
            dangerous=False
        )
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        valid, error = self.validate_params(params)
        if not valid:
            return ToolResult(success=False, error=error)
        
        action = params.get("action")
        lat = params.get("latitude")
        lon = params.get("longitude")
        
        try:
            if action == "current":
                return await self._get_current(lat, lon)
            elif action == "forecast":
                return await self._get_forecast(lat, lon, params.get("days", 7))
            else:
                return ToolResult(success=False, error=f"Unknown action: {action}")
        
        except Exception as e:
            logger.error(f"Weather tool error: {e}")
            return ToolResult(success=False, error=str(e))
    
    async def _get_current(self, lat: float, lon: float) -> ToolResult:
        """Get current weather"""
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", 
                       "precipitation", "weather_code", "wind_speed_10m"],
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        
        current = data.get("current", {})
        
        return ToolResult(success=True, data={
            "temperature_c": current.get("temperature_2m"),
            "temperature_f": current.get("temperature_2m", 0) * 9/5 + 32,
            "humidity": current.get("relative_humidity_2m"),
            "feels_like_c": current.get("apparent_temperature"),
            "precipitation": current.get("precipitation"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "weather_code": current.get("weather_code"),
        })
    
    async def _get_forecast(self, lat: float, lon: float, days: int) -> ToolResult:
        """Get weather forecast"""
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum",
                     "weather_code"],
            "forecast_days": min(days, 14),
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        
        daily = data.get("daily", {})
        dates = daily.get("time", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        precip = daily.get("precipitation_sum", [])
        codes = daily.get("weather_code", [])
        
        forecast = []
        for i in range(len(dates)):
            forecast.append({
                "date": dates[i],
                "temp_max_c": max_temps[i] if i < len(max_temps) else None,
                "temp_min_c": min_temps[i] if i < len(min_temps) else None,
                "precipitation_mm": precip[i] if i < len(precip) else None,
                "weather_code": codes[i] if i < len(codes) else None,
            })
        
        return ToolResult(success=True, data={"forecast": forecast, "days": len(forecast)})


class ToolRegistry:
    """
    Central registry for all available tools.
    
    Manages tool registration, discovery, and execution.
    """
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_builtin_tools()
    
    def _register_builtin_tools(self):
        """Register all built-in tools"""
        self.register(GitHubTool())
        self.register(SystemTool())
        self.register(WeatherTool())
    
    def register(self, tool: BaseTool) -> None:
        """Register a new tool"""
        name = tool.definition.name
        self._tools[name] = tool
        logger.info(f"Registered tool: {name}")
    
    def unregister(self, name: str) -> bool:
        """Unregister a tool by name"""
        if name in self._tools:
            del self._tools[name]
            logger.info(f"Unregistered tool: {name}")
            return True
        return False
    
    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """List all registered tool names"""
        return list(self._tools.keys())
    
    def get_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions for LLM consumption (OpenAI function format)"""
        definitions = []
        
        for tool in self._tools.values():
            defn = tool.definition
            
            # Convert to OpenAI function format
            params_schema = {
                "type": "object",
                "properties": {},
                "required": []
            }
            
            for param in defn.parameters:
                param_def = {
                    "type": param.type,
                    "description": param.description,
                }
                if param.enum:
                    param_def["enum"] = param.enum
                if param.default is not None:
                    param_def["default"] = param.default
                
                params_schema["properties"][param.name] = param_def
                
                if param.required:
                    params_schema["required"].append(param.name)
            
            definitions.append({
                "type": "function",
                "function": {
                    "name": defn.name,
                    "description": defn.description,
                    "parameters": params_schema,
                }
            })
        
        return definitions
    
    def get_tools_info(self) -> List[Dict[str, Any]]:
        """Get information about all tools"""
        info = []
        for tool in self._tools.values():
            defn = tool.definition
            info.append({
                "name": defn.name,
                "description": defn.description,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "required": p.required,
                        "description": p.description,
                    }
                    for p in defn.parameters
                ],
                "requires_confirmation": defn.requires_confirmation,
                "dangerous": defn.dangerous,
            })
        return info
    
    async def execute(self, tool_name: str, params: Dict[str, Any]) -> ToolResult:
        """Execute a tool by name"""
        tool = self._tools.get(tool_name)
        
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' not found. Available: {', '.join(self.list_tools())}"
            )
        
        logger.info(f"Executing tool '{tool_name}' with params: {params}")
        
        try:
            result = await tool.execute(params)
            return result
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return ToolResult(success=False, error=f"Execution failed: {str(e)}")


# Global registry instance
registry = ToolRegistry()
