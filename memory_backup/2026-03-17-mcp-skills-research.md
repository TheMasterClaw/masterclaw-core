# MCP Skills Research - 2026-03-17

## Research Summary

Studying MCP (Model Context Protocol) servers to expand capabilities for coordinating the 12 Disciples and building the 100-app portfolio.

---

## 🌟 HIGH-PRIORITY MCP SERVERS

### 1. **mcp-use** (9.4k stars)
- **Repo:** https://github.com/mcp-use/mcp-use
- **What it is:** Full-stack MCP framework with OpenClaw tag
- **Key Features:**
  - Aggregator and runner for MCP servers
  - Webapp for using any MCP server as an agent
  - Support for OpenAI, Anthropic, Groq, and more
  - Auto-configuration of MCP servers
  - Built-in MCP registry
- **For Our Stack:**
  - This is THE framework to run all other MCP servers
  - Has explicit "openclaw" support in tags
  - Can manage multiple MCP servers centrally
  - Web UI for managing agents
- **Installation:** `pip install mcp-use` or `uv pip install mcp-use`

---

### 2. **DesktopCommanderMCP** (5.7k stars)
- **Repo:** https://github.com/wonderwhy-er/DesktopCommanderMCP
- **What it is:** Terminal + file system + diff-based editing
- **Key Tools:**
  - Terminal command execution with timeout control
  - File operations (read/write/search)
  - Diff-based file editing (preview before apply)
  - Process management
  - Directory traversal
- **For Our Stack:**
  - Replaces/supplements my current shell/file tools
  - Diff-based editing is safer than direct writes
  - Better for code reviews and changes
- **Installation:** `npx @wonderwhy-er/desktop-commander`

---

### 3. **Playwright MCP** (Microsoft Official) (5.3k stars)
- **Repo:** https://github.com/microsoft/playwright-mcp
- **What it is:** Browser automation via accessibility tree (not screenshots)
- **Key Features:**
  - Uses Playwright's accessibility tree (LLM-friendly, no vision needed)
  - Deterministic tool application
  - Headless or headed modes
  - Supports Chrome, Firefox, WebKit
  - Network interception and mocking
  - Storage state management (cookies, localStorage)
  - PDF generation
  - Video recording
  - DevTools integration
- **Tools Available:**
  - Navigation (goto, back, forward)
  - Interaction (click, type, fill form, select)
  - Evaluation (run JavaScript)
  - Screenshots and PDFs
  - Network monitoring
  - Storage management
  - Testing assertions
- **For Our Stack:**
  - Test all 100 apps automatically
  - Screenshot validation for UI consistency
  - Form automation for user workflows
  - Scrape competitor sites for research
- **Installation:** `npx @playwright/mcp@latest`

---

### 4. **MCP Filesystem** (Official)
- **Repo:** Part of modelcontextprotocol/servers
- **What it is:** Secure file operations with configurable access controls
- **Key Features:**
  - Read/write files with UTF-8 text
  - Read images/audio as base64
  - Edit files with pattern matching (git-style diff)
  - Directory operations (list, create, tree)
  - File search with glob patterns
  - Metadata inspection
  - Dynamic roots (client can update allowed directories)
- **Safety:**
  - Restricted to allowed directories only
  - Tool annotations (readOnly, destructive, idempotent hints)
  - Dry-run mode for edits
- **For Our Stack:**
  - Safer replacement for raw file operations
  - Sandboxed access per project
  - Good for disciple workspace isolation
- **Installation:** `npx @modelcontextprotocol/server-filesystem /allowed/path`

---

### 5. **MCP Git** (Official)
- **Repo:** Part of modelcontextprotocol/servers
- **What it is:** Git repository interaction and automation
- **Key Tools:**
  - git_status - working tree status
  - git_diff_unstaged - unstaged changes
  - git_diff_staged - staged changes
  - git_diff - compare branches/commits
  - git_commit - record changes
  - git_add - stage files
  - git_reset - unstage all
  - git_log - commit history with date filtering
  - git_create_branch - create branches
  - git_checkout - switch branches
  - git_show - view commit contents
  - git_branch - list branches
- **For Our Stack:**
  - Coordinate code across all 12 disciples
  - Automated PR review workflows
  - Branch management
  - Commit history analysis
- **Installation:** `uvx mcp-server-git` or `docker run mcp/git`

---

## 🔧 OTHER NOTABLE MCP SERVERS

### 6. **MCP Memory** (Official)
- **What it is:** Knowledge graph-based persistent memory
- **Features:**
  - Entity and relation management
  - Persistent storage across sessions
  - Graph-based knowledge structure
- **For Our Stack:** Could replace file-based memory with structured graph

### 7. **MCP Sequential Thinking**
- **What it is:** Dynamic problem-solving through thought sequences
- **Features:**
  - Break down complex problems
  - Step-by-step reasoning
  - Reflection and revision
- **For Our Stack:** Architecture planning, debugging complex issues

### 8. **MCP Fetch**
- **What it is:** Web content fetching for LLM usage
- **Features:**
  - Fetch and convert web content
  - Efficient for LLM context
- **For Our Stack:** Research, documentation lookup

### 9. **MCP Time**
- **What it is:** Time and timezone conversions
- **For Our Stack:** Scheduling, coordination across timezones

---

## 🏢 COMMERCIAL/ENTERPRISE MCP SERVERS (Reference)

### Database MCPs
- **PostgreSQL MCP** (archived) - Read-only DB access with schema inspection
- **SQLite MCP** (archived) - Database interaction and BI
- **dbhub** (mentioned in list) - Multi-database support

### GitHub/GitLab
- **GitHub MCP** (archived) - Repository management, file ops, GitHub API
- **GitLab MCP** (archived) - GitLab project management

### Cloud Storage
- **Google Drive MCP** (archived) - File access and search
- **AWS KB Retrieval** (archived) - AWS Knowledge Base access

### Communication
- **Slack MCP** (now Zencoder) - Channel management and messaging
- **GeneralBots/botserver** (from list) - WhatsApp/SMS/multi-platform

---

## 🤖 AGENT/AUTOMATION TOOLS (from list)

### 10. **bolt.diy** (from stackblitz-labs)
- **Repo:** https://github.com/stackblitz-labs/bolt.diy
- **What it is:** Open-source AI coding assistant (Bolt.new alternative)
- **Key Features:**
  - 19+ AI provider integrations (OpenAI, Anthropic, Google, Groq, etc.)
  - MCP support built-in
  - Full-stack web development in browser
  - Electron desktop app
  - Git integration
  - Deploy to Netlify/Vercel/GitHub Pages
  - Supabase integration
  - Data visualization
- **For Our Stack:**
  - Rapid prototyping for the 100 apps
  - Disciples can use this for quick app generation
  - MCP integration means it can use all these tools
- **License:** MIT (but WebContainers API needs commercial license for production)

### 11. **OpenBB** (Financial Data Platform)
- **Repo:** https://github.com/OpenBB-finance/openbb
- **What it is:** Financial data platform for analysts and AI agents
- **Key Features:**
  - Python library for financial data
  - MCP server included
  - REST API
  - Multiple data sources
  - AI agent integration
- **For Our Stack:**
  - If any apps need financial data
  - Good for fintech apps in the portfolio
- **Installation:** `pip install openbb`

---

## 📋 INTEGRATION RECOMMENDATIONS

### Phase 1: Core Infrastructure
1. **mcp-use** - Central MCP management
2. **DesktopCommanderMCP** - Safer file/terminal operations
3. **MCP Git** - Repository management

### Phase 2: Development & Testing
4. **Playwright MCP** - Browser automation for testing
5. **MCP Filesystem** - Sandboxed file access
6. **bolt.diy** - Rapid app prototyping

### Phase 3: Specialized Tools
7. **MCP Memory** - Structured knowledge graph
8. **MCP Sequential Thinking** - Complex problem solving
9. **Database MCPs** - Data persistence

---

## 🔒 SECURITY CONSIDERATIONS

- All MCP servers with file system access need sandboxing
- Use allowed directories/roots to restrict access
- Tool annotations help identify destructive operations
- Prefer dry-run modes for file edits
- Secrets should be in environment variables, not code

---

## 💻 LOCAL DEPLOYMENT NOTES

Given our 125GB RAM, 1.6TB free space workstation:
- Can run multiple MCP servers as persistent services
- Docker containers for isolation
- Node.js and Python environments both available
- Can run bolt.diy locally for full control

---

## 📚 RESOURCES

- **MCP Spec:** https://modelcontextprotocol.io/
- **MCP Registry:** https://registry.modelcontextprotocol.io/
- **Official Servers:** https://github.com/modelcontextprotocol/servers
- **SDKs:** TypeScript, Python, Go, Rust, C#, Java, Kotlin, PHP, Ruby, Swift

---

*Research completed: 2026-03-17*
*Next steps: Implement mcp-use as the central orchestrator*
