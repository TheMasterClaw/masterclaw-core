# MCP Servers Installation Status
**Date:** 2026-03-17  
**System:** MasterClaw (125GB RAM, 1.6TB storage)

---

## ✅ INSTALLED MCP SERVERS

### Python-based (via uv/pip)
| Server | Status | Purpose |
|--------|--------|---------|
| mcp-use | ✅ | Central MCP orchestrator framework |
| mcp-server-git | ✅ | Git repository management |
| playwright-mcp | ✅ | Browser automation (Python bindings) |

### Node.js-based (via npm)
| Server | Status | Purpose |
|--------|--------|---------|
| @playwright/mcp | ✅ | Browser automation (official Microsoft) |
| @wonderwhy-er/desktop-commander | ✅ | Terminal + filesystem + diff editing |
| @modelcontextprotocol/server-filesystem | ✅ | Secure file operations |

### Cloned Repos
| Repo | Location | Status |
|------|----------|--------|
| mcp-servers-official | ~/.openclaw/mcp-servers/mcp-servers-official | ✅ |
| bolt.diy | ~/.openclaw/mcp-servers/bolt.diy | ✅ |

---

## 🔧 MCP CONFIGURATION

Config file: `~/.openclaw/mcp-config.json`

### Available Servers:

1. **filesystem** - Secure file operations in workspace
   ```json
   {
     "command": "npx",
     "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/holyspirit/.openclaw/workspace"]
   }
   ```

2. **desktop-commander** - Terminal and file editing
   ```json
   {
     "command": "npx",
     "args": ["-y", "@wonderwhy-er/desktop-commander"]
   }
   ```

3. **playwright** - Browser automation
   ```json
   {
     "command": "npx",
     "args": ["-y", "@playwright/mcp@latest"]
   }
   ```

4. **git** - Git repository operations
   ```json
   {
     "command": "uvx",
     "args": ["mcp-server-git"]
   }
   ```

5. **memory** - Knowledge graph memory
   ```json
   {
     "command": "uvx",
     "args": ["mcp-server-memory"]
   }
   ```

6. **sequential-thinking** - Problem-solving workflows
   ```json
   {
     "command": "uvx",
     "args": ["mcp-server-sequentialthinking"]
   }
   ```

7. **time** - Time and timezone utilities
   ```json
   {
     "command": "uvx",
     "args": ["mcp-server-time"]
   }
   ```

---

## 🚀 USAGE

### For Claude Desktop:
Copy `~/.openclaw/mcp-config.json` to:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

### For Claude Code:
```bash
claude mcp add filesystem -- npx -y @modelcontextprotocol/server-filesystem /home/holyspirit/.openclaw/workspace
claude mcp add desktop-commander -- npx -y @wonderwhy-er/desktop-commander
claude mcp add playwright -- npx -y @playwright/mcp@latest
claude mcp add git -- uvx mcp-server-git
```

### For Other MCP Clients:
Use the JSON configuration in `~/.openclaw/mcp-config.json`

---

## 🛠️ TOOLS AVAILABLE

### DesktopCommanderMCP
- `execute_command` - Run terminal commands
- `read_file` - Read file contents
- `write_file` - Write to files
- `edit_block` - Diff-based file editing
- `search_files` - Search file contents
- `list_directory` - Directory listing
- `create_directory` - Create directories
- `move_file` - Move/rename files
- `get_file_info` - File metadata
- `list_processes` - Running processes
- `kill_process` - Terminate processes

### Playwright MCP
- `browser_navigate` - Navigate to URLs
- `browser_click` - Click elements
- `browser_type` - Type text
- `browser_fill_form` - Fill forms
- `browser_take_screenshot` - Capture screenshots
- `browser_evaluate` - Run JavaScript
- `browser_snapshot` - Page accessibility tree
- `browser_console_messages` - Get console logs
- `browser_network_requests` - Monitor network

### Git MCP
- `git_status` - Working tree status
- `git_add` - Stage files
- `git_commit` - Create commits
- `git_diff` - Show diffs
- `git_log` - Commit history
- `git_branch` - List branches
- `git_checkout` - Switch branches
- `git_create_branch` - Create branches

### Filesystem MCP
- `read_text_file` - Read files
- `write_file` - Write files
- `edit_file` - Edit with diff preview
- `list_directory` - List contents
- `search_files` - Search files
- `get_file_info` - File metadata

---

## 📁 DIRECTORY STRUCTURE

```
~/.openclaw/
├── mcp-env/                    # Python virtual environment
│   ├── bin/                    # Executables
│   └── lib/                    # Python packages
├── mcp-servers/                # Cloned repositories
│   ├── mcp-servers-official/   # Official MCP servers
│   │   └── src/
│   │       ├── filesystem/
│   │       ├── git/
│   │       ├── memory/
│   │       ├── sequentialthinking/
│   │       └── time/
│   └── bolt.diy/               # Rapid prototyping tool
├── mcp-config.json             # MCP server configuration
└── install-mcp-servers.sh      # Re-installation script
```

---

## 🔄 ACTIVATION

To use the Python MCP servers:
```bash
source ~/.openclaw/mcp-env/bin/activate
```

Or prefix commands with:
```bash
~/.openclaw/mcp-env/bin/python
```

---

## ⚠️ NOTES

- Python MCP servers installed in isolated virtual environment
- Node.js MCP servers installed globally via npm
- All servers configured to work with local workspace at `/home/holyspirit/.openclaw/workspace`
- bolt.diy available for rapid app prototyping with 19+ LLM providers

---

## 📚 NEXT STEPS

1. **Install QMD memory backend:**
   ```bash
   export PATH="$HOME/.bun/bin:$PATH"
   bun install qmd
   ```

2. **Install Lossless Claw plugin:**
   ```bash
   openclaw plugins install @martian-engineering/lossless-claw
   ```

3. **Configure memory in openclaw.json:**
   Already done - `memory.backend` set to `qmd`

4. **Restart OpenClaw** to apply changes

---

*Generated by MasterClaw / Holy Spirit*
