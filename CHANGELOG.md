# Changelog

All notable changes to MasterClaw Core will be documented in this file.

## [Unreleased]

### Added: Troubleshooting Guide and Diagnostic Assistant (`mc troubleshoot`) 🔧
- **New Feature**: Interactive troubleshooting wizard for common MasterClaw issues
  - **Purpose**: Help users diagnose and fix problems without searching documentation
  - **Benefit**: Faster issue resolution with guided solutions

- **New Commands**:
  - `mc troubleshoot wizard` — Interactive troubleshooting wizard
    - Step-by-step diagnosis with category selection
    - Symptom matching to identify issues
    - Guided solution execution
  - `mc troubleshoot list` — List all common issues
    - Filter by category: `--category docker`
    - Filter by severity: `--severity critical`
  - `mc troubleshoot guide <issue>` — Detailed troubleshooting guide
    - Symptoms, diagnosis steps, and solutions
    - Prevention tips for each issue
  - `mc troubleshoot diagnose` — Quick diagnostic checks
    - Fast system health overview
    - Identifies common problems

- **Covered Issues** (8 common problems):
  | Issue | Severity | Category |
  |-------|----------|----------|
  | Services Not Starting | 🔴 Critical | docker |
  | SSL Certificate Problems | 🔴 High | ssl |
  | High Memory Usage | 🔴 High | performance |
  | Database Connection Problems | 🔴 Critical | database |
  | LLM API Connection Errors | 🔴 High | api |
  | Backup Not Working | 🟡 Medium | backup |
  | Slow Response Times | 🟡 Medium | performance |
  | Notifications Not Working | 🟢 Low | notifications |

- **Features**:
  - Interactive wizard with inquirer prompts
  - One-click solution execution
  - Prevention recommendations
  - Quick diagnostic mode
  - Severity-based prioritization

- **Files Added**:
  - `lib/troubleshoot.js` - Troubleshooting module (~600 lines)
  - Updated `bin/mc.js` - Registered `mc troubleshoot` command
  - Updated `README.md` - Added comprehensive documentation

### Added: Configuration Template Generator (`mc template`) 📄
- **New Feature**: Generate starter configuration files for MasterClaw deployments
  - **Purpose**: Simplify onboarding and ensure consistent configuration
  - **Benefit**: New users can generate valid configs without reading docs

- **New Commands**:
  - `mc template list` — List all available templates
  - `mc template generate <template>` — Generate a configuration file
    - Supports `--interactive` mode with prompts
    - Custom output path with `-o, --output`
    - Force overwrite with `--force`
  - `mc template show <template>` — Preview template output
  - `mc template wizard` — Interactive wizard for generating configs

- **Available Templates**:
  - `env` — Complete .env file with all settings
  - `docker-override` — Docker Compose override for local development
  - `terraform-vars` — Terraform variables for AWS deployment
  - `service` — Template for adding custom services
  - `monitoring` — Prometheus/Grafana alert rules
  - `backup` — Cloud backup configuration

- **Features**:
  - Interactive prompts for required values
  - Smart defaults based on environment type
  - Auto-generated secure tokens
  - Validation-ready output

- **Files Added**:
  - `lib/template.js` - Template generator module (~600 lines)
  - Updated `bin/mc.js` - Registered `mc template` command
  - Updated `README.md` - Added comprehensive documentation

### Added: Terraform Infrastructure Management (`mc terraform`) 🏗️
- **New Feature**: Complete Terraform Infrastructure as Code (IaC) management via CLI
  - **Purpose**: Bridge the gap between Terraform infrastructure code and CLI usability
  - **Benefit**: Deploy and manage AWS cloud infrastructure without leaving the terminal

- **New Commands**:
  - `mc terraform status` — Show Terraform status and environment information
    - Check prerequisites (Terraform, AWS CLI)
    - View initialization status and workspace
    - Show cluster endpoints if deployed
    - JSON output support with `--json`
  - `mc terraform env` — List available environments (dev, staging, prod)
  - `mc terraform init` — Initialize Terraform for an environment
    - Support for `--upgrade` to update providers
    - Support for `--reconfigure` for backend changes
  - `mc terraform validate` — Validate Terraform configuration files
  - `mc terraform plan` — Show execution plan
    - Save plans to file with `-o, --output`
    - Support for `--destroy` planning
  - `mc terraform apply` — Apply Terraform changes
    - Production warnings before apply
    - Auto-approve option for automation (`--auto-approve`)
    - Apply saved plans with `-p, --plan`
    - Target specific resources with `--target`
  - `mc terraform destroy` — Destroy infrastructure (with safety confirmations)
    - Explicit confirmation required for production
    - Target specific resources with `--target`
  - `mc terraform output` — Show Terraform outputs
    - JSON output support (`--json`)
    - Raw single value output (`--raw`)
    - Connection details and endpoints
  - `mc terraform kubeconfig` — Configure kubectl for EKS cluster
    - Automatic cluster name detection
    - Custom region support (`--region`)

- **Features**:
  - Environment management for dev, staging, and production
  - Pre-flight validation before operations
  - Production safety checks (explicit confirmation for destroy)
  - Automatic kubectl configuration for EKS clusters
  - Structured JSON output for automation
  - Comprehensive error handling with actionable messages

- **Files Added**:
  - `lib/terraform.js` - Complete Terraform management module (~700 lines)
  - Updated `bin/mc.js` - Registered `mc terraform` command
  - Updated `README.md` - Added comprehensive documentation

### Added: Cost Budget Alert System (`mc cost budget-*`) 💰
- **New Feature**: Comprehensive budget management with automated alerts and notifications
  - **Purpose**: Prevent surprise LLM bills by proactively monitoring spending against defined budgets
  - **Benefit**: Real-time notifications when spending thresholds are exceeded

- **New Commands**:
  - `mc cost budget-set` — Configure monthly budget and alert thresholds
    - Set monthly budget amount (`--amount`)
    - Configure warning threshold (`--warn`, default 80%)
    - Configure critical threshold (`--critical`, default 95%)
    - Enable/disable notifications (`--notifications`)
    - Set alert cooldown period (`--cooldown`)
  - `mc cost budget-show` — Display budget configuration and current spending
    - Visual progress bar showing budget usage
    - Color-coded status (healthy/warning/critical)
    - Spending projection based on 7-day average
    - JSON output support with `--json`
  - `mc cost budget-check` — Check spending against budget with notifications
    - Sends notifications when thresholds are exceeded
    - Respects alert cooldown to prevent spam
    - Returns exit codes for CI/CD integration (0=healthy, 1=warning, 2=critical)
  - `mc cost budget-monitor` — Manage automated budget monitoring
    - Enable/disable cron-based monitoring (`--enable`/`--disable`)
    - Configurable check interval (`--interval`)
    - Show monitoring status (`--status`)
  - `mc cost budget-history` — View budget alert history
    - Shows past alerts with timestamps and levels
    - Configurable limit (`--limit`)

- **Features**:
  - Persistent budget configuration stored in `config/budget.json`
  - Smart notifications with cooldown periods (default 24 hours)
  - Visual progress bars and color-coded status indicators
  - Spending projections based on recent usage patterns
  - Integration with existing notification channels (WhatsApp, Discord, Slack, Telegram)
  - Budget alert history tracking

- **Documentation**: Added comprehensive documentation in `COST_BUDGET_IMPROVEMENT.md`

### Added: Context API CLI Commands (`mc context api-*`) 🆕
- **New Feature**: Added missing CLI commands for accessing rex-deus context via Core API
  - **Purpose**: Complete the context API integration by adding commands for people, knowledge, and preferences
  - **Benefit**: Users can now query all context types remotely via API, not just projects and goals

- **New Commands**:
  - `mc context api-people` — Query people/relationships from rex-deus context via API
    - Supports filtering by `--role` (developer, designer, etc.)
    - Supports filtering by `--relationship` (friend, colleague, client)
    - JSON output support with `--json`
  - `mc context api-knowledge` — Query knowledge entries from rex-deus context via API
    - Supports filtering by `--category`
    - Supports filtering by `--confidence` (high, medium, low)
    - Groups output by category for readability
    - JSON output support with `--json`
  - `mc context api-preferences` — Query preferences from rex-deus context via API
    - Supports filtering by `--category` (Communication, Technical, etc.)
    - Supports filtering by `--priority` (required, preferred, optional)
    - Priority indicators (!, ●, ○) for quick visual scanning
    - JSON output support with `--json`

- **Consistency**: All context types (projects, goals, people, knowledge, preferences) now have corresponding API CLI commands
- **Documentation**: Added comprehensive documentation for all context API commands in README

### Security & Error Handling: HTTP Client Resource Cleanup 🔒
- **Improved**: Added AbortController support for request cancellation in http-client
  - **Purpose**: Prevents resource leaks when security validation fails (SSRF, header injection)
  - **Benefit**: Faster failure response times and proper cleanup of pending requests

- **Technical Changes**:
  - Added `createAbortController()` helper for managing request timeouts
  - Request interceptor now creates abort controllers before validation
  - Cleanup functions are properly called on SSRF validation failures
  - Cleanup functions are properly called on header validation failures
  - Response interceptor cleans up abort timers on both success and error
  - Added try/finally blocks to ensure cleanup happens on all code paths

- **New Tests**:
  - Test: SSRF validation failure triggers immediate cleanup
  - Test: Header validation failure triggers immediate cleanup  
  - Test: Dangerous URL schemes are rejected with proper cleanup
  - Test: Constants are properly exported for external use

### Added: Dashboard Command (`mc dashboard`) 📊
- **New Feature**: CLI command to open monitoring dashboards from the terminal
  - **Purpose**: Quick access to Grafana, Prometheus, Loki, Traefik, and Alertmanager dashboards
  - **Cross-platform**: Supports macOS, Linux, and Windows with automatic browser detection

- **Dashboard Commands**:
  - `mc dashboard list` — List all available dashboards with descriptions and URLs
  - `mc dashboard list --check` — Check if dashboards are accessible
  - `mc dashboard open <name>` — Open a specific dashboard in the default browser
  - `mc dashboard open <name> --url-only` — Print URL instead of opening browser
  - `mc dashboard open <name> -p <path>` — Open with a specific path (e.g., `/explore`)
  - `mc dashboard grafana` — Shortcut to open Grafana
  - `mc dashboard prometheus` — Shortcut to open Prometheus
  - `mc dashboard loki` — Shortcut to open Loki
  - `mc dashboard traefik` — Shortcut to open Traefik dashboard
  - `mc dashboard alertmanager` — Shortcut to open Alertmanager
  - `mc dashboard open-all` — Open all dashboards at once
  - `mc dashboard config <name> <url>` — Configure custom dashboard URLs

- **Dashboard Features**:
  - **Smart URL Resolution**: Uses default local URLs or custom configured URLs
  - **Cross-Platform Browser Opening**: Uses `open` (macOS), `xdg-open` (Linux), or `cmd` (Windows)
  - **Fallback Browser Detection**: On Linux, tries multiple browsers if xdg-open fails
  - **Path Support**: Append specific paths like `/explore` or `/graph` to dashboard URLs
  - **Configuration**: Store custom URLs via `mc dashboard config grafana https://grafana.mycompany.com`

- **Default URLs**:
  - Grafana: `http://localhost:3003`
  - Prometheus: `http://localhost:9090`
  - Loki: `http://localhost:3100`
  - Traefik: `http://localhost:8080`
  - Alertmanager: `http://localhost:9093`

- **Example Usage**:
  ```bash
  # List all dashboards
  mc dashboard list

  # Check which dashboards are running
  mc dashboard list --check

  # Open Grafana
  mc dashboard open grafana
  mc dashboard grafana  # shortcut

  # Open Prometheus with specific path
  mc dashboard open prometheus -p /graph

  # Configure custom Grafana URL
  mc dashboard config grafana https://grafana.mycompany.com

  # Open all dashboards
  mc dashboard open-all
  ```

- **Files Added**:
  - `masterclaw-tools/lib/dashboard.js` — Dashboard command implementation (400+ lines)
  - `masterclaw-tools/tests/dashboard.test.js` — Comprehensive test suite (31 tests)

- **Files Modified**:
  - `masterclaw-tools/bin/mc.js` — Added dashboard command registration
  - `masterclaw-tools/package.json` — Version bumped to 0.42.0

### Added: Workflow Automation System (`mc workflow`) 🔄
- **New Feature**: Comprehensive workflow automation for operational playbooks
  - **Purpose**: Define and execute reusable multi-step operational procedures
  - **Storage**: Workflows stored in `rex-deus/config/workflows/` for version control
  - **Formats**: Support for YAML (human-friendly) and JSON (programmatic)

- **Workflow Commands**:
  - `mc workflow list` — List all available workflows with descriptions
  - `mc workflow show <name>` — Display workflow details and step breakdown
  - `mc workflow create <name>` — Create from templates (standard, maintenance, incident)
  - `mc workflow run <name>` — Execute with variable substitution and rollback support
  - `mc workflow edit <name>` — Open workflow in default editor ($EDITOR)
  - `mc workflow delete <name>` — Remove workflow (with --force confirmation)
  - `mc workflow history [name]` — View execution history with timestamps
  - `mc workflow validate <name>` — Check workflow syntax and structure
  - `mc workflow export <name>` — Export workflow to stdout or file
  - `mc workflow import <file>` — Import workflow from external file

- **Workflow Features**:
  - **Variable Substitution**: Use `${VAR}` or `$VAR` syntax, resolved from workflow vars, CLI args, or environment
  - **Conditional Execution**: `if` conditions support variable comparisons
  - **Output Capture**: Save command output to variables for later steps (`capture: VAR_NAME`)
  - **Rollback Support**: Define rollback steps that execute on workflow failure
  - **Execution History**: Automatic logging of all runs to `.history/` directory
  - **Dry-Run Mode**: Preview workflow execution without running commands
  - **Environment Variables**: Per-step env var configuration
  - **Working Directory**: Per-step working directory override
  - **Error Handling**: `continueOnError` option for non-critical steps

- **Built-in Workflow Templates**:
  - `deploy-standard` — Full deployment with validation, backup, smoke tests, and rollback
  - `nightly-maintenance` — Scheduled maintenance (log cleanup, pruning, verification)
  - `incident-response` — Emergency diagnostics and log collection

- **Example Usage**:
  ```bash
  # Run deployment workflow
  mc workflow run deploy-standard
  
  # Run with custom variables
  mc workflow run deploy-standard -V ENV=staging -V SKIP_BACKUP=true
  
  # Create and edit custom workflow
  mc workflow create my-deploy --template standard
  mc workflow edit my-deploy
  
  # Schedule via cron
  0 2 * * * mc workflow run nightly-maintenance
  ```

- **Files Added**:
  - `masterclaw-tools/lib/workflow.js` — Core workflow engine (600+ lines)
  - `rex-deus/config/workflows/deploy-standard.yaml` — Standard deployment playbook
  - `rex-deus/config/workflows/nightly-maintenance.yaml` — Maintenance automation
  - `rex-deus/config/workflows/incident-response.yaml` — Emergency response
  - `rex-deus/config/workflows/README.md` — Workflow documentation

- **Files Modified**:
  - `masterclaw-tools/bin/mc.js` — Added workflow command integration
  - `masterclaw-tools/package.json` — Added js-yaml dependency, version bumped to 0.41.0

### Security Hardening: Size Module Command Injection Prevention 🔒
- **Fixed Command Injection Vulnerability** (`masterclaw-tools/lib/size.js`)
  - **Problem**: `getDirectorySize()` and `getDirectoryBreakdown()` used `execSync()` with unsanitized path interpolation
  - **Impact**: Paths from environment variables (`MASTERCLAW_INFRA_DIR`) could potentially execute arbitrary shell commands
  - **Solution**: Implemented comprehensive path validation and secure command execution
  
- **Security Functions Added**:
  - `isValidPath()`: Validates paths before use, rejects shell metacharacters (`;`, `|`, `&`, `$`, etc.), null bytes, and path traversal (`..`)
  - `escapeShellArg()`: Escapes double quotes and backslashes for safe shell usage
  - `validateAndSanitizePath()`: Combined validation with absolute path resolution
  
- **Secure Execution**:
  - Replaced `execSync()` with `execFileSync()` using arguments array (no shell invocation)
  - Added `shell: false` option to explicitly disable shell interpretation
  - All paths validated before passing to external commands
  
- **Path Traversal Prevention**:
  - Rejects paths containing `..` components before normalization
  - Resolves relative paths to absolute before use
  - Validates environment variable paths before use

- **Error Handling**:
  - Graceful degradation: returns 0/empty array for invalid paths instead of crashing
  - Validates `maxDepth` parameter to prevent abuse
  - Verifies paths are actual directories (not files) before processing

- **Comprehensive Tests**: Added `masterclaw-tools/tests/size.test.js` with **63 tests**:
  - **18 security tests**: Command injection prevention, path traversal, null byte injection
  - **12 path validation tests**: Shell metacharacters, environment variables, traversal patterns
  - **17 functionality tests**: Byte formatting, size parsing, directory calculations
  - **16 integration tests**: Real filesystem operations with temp directories
  
- **Files modified**:
  - `masterclaw-tools/lib/size.js` — Added security utilities and hardened existing functions
  - `masterclaw-tools/tests/size.test.js` — New comprehensive test suite (63 tests)

### Added
- **Docker System Prune Command** (`mc prune`) 🆕
  - Comprehensive Docker resource management for images, containers, volumes, networks, and build cache
  - **Disk usage overview**: Shows total usage, reclaimable space, and percentage savings by category
  - **Selective pruning**: Target specific resources with `--images`, `--containers`, `--volumes`, `--cache`, `--networks`
  - **Dry-run mode**: Preview what would be pruned without removing anything (`--dry-run`)
  - **Safety features**:
    - MasterClaw service protection (containers starting with `mc-` are never pruned)
    - Confirmation prompts before destructive operations (skip with `--force`)
    - Dangling-only option for safe image cleanup (`--dangling-only`)
  - **Subcommands**:
    - `mc prune` — Show disk usage overview
    - `mc prune --images` — Prune unused images
    - `mc prune --containers` — Prune stopped containers
    - `mc prune --volumes` — Prune unused volumes
    - `mc prune --cache` — Prune build cache
    - `mc prune --all` — Prune everything
    - `mc prune --dry-run` — Preview mode
    - `mc prune quick` — Quick prune with safe defaults (dangling images + stopped containers + unused networks)
    - `mc prune detail` — Show detailed resource breakdown
  - **Smart recommendations**: Suggests pruning when >1GB reclaimable or >50% image space wasted
  - **Comprehensive tests**: Added `masterclaw-tools/tests/prune.test.js` with 44 tests
  - **New files**:
    - `masterclaw-tools/lib/prune.js` — Prune command implementation (649 lines)
    - `masterclaw-tools/tests/prune.test.js` — Test suite (44 tests)
  - **Modified files**:
    - `masterclaw-tools/bin/mc.js` — Added prune command registration
    - `masterclaw-tools/package.json` — Version bump to 0.37.0

- **Quickstart Wizard** (`mc quickstart`) 🆕
  - Interactive project bootstrap wizard for new MasterClaw projects
  - **Three templates**: Minimal, Standard, and Complete project setups
  - **Interactive prompts**: Project name, template selection, LLM provider, Docker/git options
  - **Automatic setup**:
    - Directory structure (data/, memory/, skills/, logs/)
    - Configuration files (.env, config.json)
    - Docker Compose setup (optional)
    - Sample memory files
    - Git initialization (optional)
  - **LLM provider presets**: OpenAI, Anthropic, Google, Ollama
  - **Non-interactive mode**: Use `--yes` flag for defaults
  - **Complete template extras**: Backup scripts, CI/CD workflows, health checks
  - **New files**:
    - `masterclaw-tools/lib/quickstart.js` — Quickstart command implementation
  - **Modified files**:
    - `masterclaw-tools/bin/mc.js` — Added quickstart command registration
    - `masterclaw-tools/package.json` — Version bump to 0.36.0

### Security Hardening: Contacts Input Validation 🔒
- **Comprehensive Input Validation** (`masterclaw-tools/lib/contacts.js`)
  - **Contact Name Validation**: Max 100 chars, control character rejection, special character ratio limits (>30% rejected)
  - **Email Validation**: RFC 5322 compliant format checking
  - **Phone Validation**: International format support with digit/character filtering
  - **URL Validation**: Scheme enforcement (http/https only), blocks `javascript:` and other dangerous schemes
  - **Tag Validation**: Alphanumeric with hyphens only, max 50 chars per tag
  - **Search Query Validation**: Regex special character sanitization (ReDoS prevention), max 200 chars
  - **Export Filename Validation**: Path traversal prevention (`../`, `..\` blocked), basename extraction

- **Data Sanitization**:
  - All loaded contacts automatically sanitized to prevent injection from tampered files
  - Markdown sanitization for safe rendering (escapes `*`, `_`, `[`, `]`, etc.)
  - CSV injection prevention: Formula characters (`=`, `+`, `-`, `@`) prefixed with single quote
  - Truncation of oversized fields (DoS prevention)
  - Filtering of invalid contact methods and tags

- **Security Tests**: Added `masterclaw-tools/tests/contacts.validation.test.js` with 41 tests covering:
  - Name validation (empty, control chars, length, special char ratio)
  - Email/phone/URL format validation
  - Tag and search query validation
  - Export filename security (path traversal)
  - Markdown sanitization
  - Contact object sanitization
  - CSV injection prevention

- **Documentation**: Updated `SECURITY.md` with contacts security section
- **Files modified**: `masterclaw-tools/lib/contacts.js`
- **Files added**: `masterclaw-tools/tests/contacts.validation.test.js` (41 tests)

### Security & Error Handling Improvements
- **Client Generator Security Hardening** (`masterclaw-tools/lib/client.js`) 🔒
  - **SSRF Protection**: Replaced raw `axios` with secure `http-client` that validates URLs against SSRF attacks
  - **Centralized Error Handling**: All commands now use `wrapCommand()` for consistent error handling with proper exit codes
  - **Rate Limiting**: Added rate limiting to all `mc client` subcommands to prevent abuse
  - **Input Validation**: Added URL format validation and language option validation
  - **Bug Fix**: Fixed Python template syntax error (`or` → `||` in template literals)
  - **Comprehensive Tests**: Added `masterclaw-tools/tests/client.test.js` with 65 tests covering:
    - SSRF protection validation
    - Rate limiting integration
    - Error handling scenarios
    - Client code generation logic
    - Metadata management
    - Security features
  - **Files modified**: `masterclaw-tools/lib/client.js`
  - **Files added**: `masterclaw-tools/tests/client.test.js` (65 tests)

### Added
- **Deployment Notifications** (`mc deploy --notify`) 🆕
  - Automatic notifications to Discord, Slack, Telegram, WhatsApp when deployments occur
  - **Notification types**: deployment started, successful, failed, rolled back
  - **Rich context**: Includes version, color (blue/green), duration, initiator, error details
  - **New commands**:
    - `mc deploy rolling --notify` — Deploy with notifications
    - `mc deploy canary 10 --notify` — Canary deployment with notifications
    - `mc deploy rollback --notify` — Rollback with notifications
    - `mc deploy notify --enable` — Enable deployment notifications
    - `mc deploy notify --disable` — Disable deployment notifications
    - `mc deploy notify-test` — Send test deployment notification
  - **Backward compatible**: Opt-in via `--notify` flag, existing workflows unchanged
  - **Integration**: Uses existing notification channels configured via `mc notify`
  - **Graceful degradation**: Notification failures don't affect deployment success
  - **Files modified**: `masterclaw-tools/lib/deploy.js`
  - **Files added**: `masterclaw-tools/tests/deploy.notifications.test.js` (22 tests)
  - Version bump to 0.34.0

### Added
- **Logger Flush on Process Exit** — Ensures critical logs are persisted during crashes 🆕
  - Added `flushLogger()` integration in error handler for all exit scenarios
  - Modified `setupGlobalErrorHandlers()` to flush logs before `process.exit()` on:
    - `unhandledRejection` — Async errors that crash the process
    - `uncaughtException` — Synchronous errors that crash the process  
    - `SIGINT` — User interrupt (Ctrl+C)
    - `SIGTERM` — Graceful termination signal
  - Enhanced `logger.flush()` to write buffered messages before closing stream
  - Enhanced `logger.shutdown()` to flush buffered messages before cleanup
  - Prevents loss of critical audit logs and security events during unexpected exits
  - Added comprehensive test suite: `masterclaw-tools/tests/logger.flush.test.js`
  - **Security**: Security violations and audit events are now guaranteed to be persisted
  - **Files modified**: `lib/error-handler.js`, `lib/logger.js`
  - **Files added**: `tests/logger.flush.test.js`

### Added
- **Intelligent Log Analysis Command** (`mc analyze`) 🆕
  - New `mc analyze` command for automated log analysis and anomaly detection
  - **Pattern Detection** — Identifies 9 error categories: runtime, network, resource exhaustion, security, SSL, database, health, performance, rate limiting
  - **Anomaly Detection** — Detects error spikes (3x average), repeated errors, service error concentration
  - **Security Analysis** — Flags authentication failures, suspicious access patterns
  - **Actionable Insights** — Provides specific remediation commands (e.g., `mc doctor`, `mc ssl check`)
  - **Time window analysis** — Supports 1h, 6h, 24h, 7d windows
  - **Service-specific analysis** — Analyze specific service or all services
  - **Subcommands/Options**:
    - `mc analyze` — Analyze all services (last hour)
    - `mc analyze --service core` — Analyze specific service
    - `mc analyze --time 24h` — Analyze last 24 hours
    - `mc analyze --focus critical` — Focus on critical issues
    - `mc analyze --focus security` — Focus on security events
    - `mc analyze --verbose` — Show detailed error patterns
    - `mc analyze --json` — Output as JSON for automation
  - **Health scoring** — Overall health status: HEALTHY, DEGRADED, WARNING, CRITICAL
  - **CI/CD integration** — Returns exit code 1 for critical issues
  - **New files**: `masterclaw-tools/lib/analyze.js` (module), updated `bin/mc.js` (CLI registration)
  - Version bump to 0.32.0

- **Real-Time Container Resource Monitor** (`mc top`) 🆕
  - New `mc top` command - like `htop` but for MasterClaw services
  - **Real-time monitoring** — Auto-updating display of container CPU, memory, network I/O
  - **Categorized view** — Services grouped by type (App, Data, Infrastructure, Monitoring)
  - **Visual indicators** — Color-coded usage levels (green/yellow/red), health status icons
  - **Trend detection** — Arrows show CPU usage trending up/down vs previous sample
  - **Subcommands/Options**:
    - `mc top` — Start interactive watch mode (default)
    - `mc top --once` — Single snapshot, no refresh
    - `mc top --interval 5` — Custom refresh interval (seconds)
    - `mc top --json` — Output as JSON for scripting
    - `mc top --export stats.json` — Export to file
  - **Display columns**: Container, Status, CPU%, Memory, Mem%, Net I/O, PIDs, Uptime
  - **Docker system summary** — Shows total containers, images, volumes with sizes
  - **Services monitored**: traefik, interface, backend, core, gateway, chroma, watchtower, grafana, prometheus, loki
  - **New files**: `masterclaw-tools/lib/top.js` (module), updated `bin/mc.js` (CLI registration)
  - **Security**: Rate limiting on watch mode, input validation for interval values
  - Version bump to 0.29.0

- **Alias Management Command** (`masterclaw-tools/lib/alias.js`)
  - New `mc alias` command for managing CLI aliases and shortcuts
  - **Command aliases**: Short aliases for frequently used commands (e.g., `s` → `status`, `l` → `logs`)
  - **Shell shortcuts**: Full shell commands for complex workflows
  - **Subcommands**:
    - `mc alias list` - Show all aliases and shortcuts (with `--json` option)
    - `mc alias run <name>` - Execute an alias or shortcut
    - `mc alias add <name> <command>` - Add new command alias
    - `mc alias add <name> <command> --shortcut` - Add shell shortcut
    - `mc alias show <name>` - Display alias details
    - `mc alias remove <name>` - Delete an alias
    - `mc alias export [file]` - Export aliases to JSON
    - `mc alias import <file>` - Import aliases (with `--merge` option)
    - `mc alias reset --force` - Reset to defaults
  - **Default aliases**: 17 pre-configured aliases (s, st, l, log, b, bk, r, u, d, cfg, ex, ev, nt, perf, sm, val)
  - **Default shortcuts**: 7 pre-configured shortcuts (deploy, logs-backend, logs-core, logs-gateway, quick-status, full-backup, health-watch)
  - **Security features**: Rate limiting on all operations, input validation for alias names
  - **Integration**: Stores aliases in rex-deus config (`~/.openclaw/workspace/rex-deus/config/aliases.json`)
  - Version bump to 0.27.0

### Testing Improvements
- **Comprehensive Analytics Module Test Suite** (`tests/test_analytics.py`) 🆕
  - Added **37 new tests** providing complete coverage of the analytics/cost tracking module
  - **Test coverage includes**:
    - Cost calculation tests for all supported providers (OpenAI, Anthropic) and models
    - CostTracker functionality: single/multiple entries, date filtering, aggregation
    - Analytics metrics: request tracking, chat tracking, memory search tracking
    - Statistics computation: error rates, response times, provider usage breakdowns
    - Pricing validation: ensures all models have correct pricing structure
    - Edge cases: zero tokens, negative tokens, large token counts, unknown providers/models
  - **Test organization**:
    - `TestCalculateCost` (8 tests) - cost calculation accuracy across providers
    - `TestCostTracker` (11 tests) - cost tracking, summaries, daily breakdowns
    - `TestAnalytics` (10 tests) - metrics tracking and statistics computation
    - `TestPricingConstants` (4 tests) - pricing structure validation
    - `TestEdgeCases` (4 tests) - boundary conditions and error handling
  - **Benefits**: Prevents cost calculation regressions, ensures accurate billing, validates pricing updates
  - Fills critical testing gap in financial/usage tracking functionality

### Security Hardening & Reliability Improvements
- **Input Validation & Bounds Checking for `mc top` Command** (`masterclaw-tools/lib/top.js`)
  - **Security Fix**: Added `validateInterval()` function to prevent DoS attacks via resource exhaustion
  - **Bounds enforcement**: Interval must be between 1 second (min) and 300 seconds/5 minutes (max)
  - **DoS Prevention**: Prevents attackers from setting extremely low intervals (e.g., 0.001s) to overwhelm Docker API
  - **Input sanitization**: Validates interval is a finite number, rejects Infinity, NaN, and non-numeric values
  - **Graceful degradation**: Falls back to default 3-second interval with warning message on invalid input
  - **Comprehensive test coverage**: Added 16 new test cases covering valid inputs, boundary values, and attack vectors
  - **Security audit logging**: Warn-level logs for invalid interval attempts with context
- **Test Framework Standardization** (`masterclaw-tools/tests/http-client.test.js`)
  - Converted test file from `node:test` to Jest framework for consistency
  - Fixed failing test by properly importing SERVICES from services module
  - Standardized test syntax with Jest matchers (toBe, toHaveLength, etc.)
  - Improved test organization with clear describe blocks
  - All 20 tests now pass successfully
- **Memory ID Generation Security** (`masterclaw_core/memory.py`)
  - **Replaced MD5 with SHA-256** for memory ID generation in both backends
    - MD5 is cryptographically broken and vulnerable to collision attacks
    - SHA-256 provides 256-bit security vs MD5's broken 128-bit (effectively 64-bit) security
    - IDs remain 32 hex characters for backward compatibility (truncated SHA-256)
    - Updated `ChromaBackend.add()` and `JSONBackend.add()` methods
    - No breaking changes - existing IDs remain valid, new IDs use stronger algorithm
- **Performance Module Security Enhancements** (`lib/performance.js`)
  - **Input validation** for all numeric parameters (`n`, `limit`) with DoS protection
    - Bounds checking prevents excessive values (max 100 endpoints, 1000 profiles)
    - Safe integer validation prevents integer overflow attacks
    - Type coercion with validation for string inputs
  - **Correlation ID integration** for distributed tracing across API calls
    - Automatic propagation via `x-correlation-id` HTTP header
    - Enables end-to-end request tracing through the Core API
  - **Exponential backoff retry logic** for resilient API communication
    - 3 retries with configurable initial delay (500ms) and max delay (5s)
    - Jitter (±25%) prevents thundering herd on service recovery
    - Only retries transient errors (network, 502/503/504/429 status codes)
  - **Response size limiting** (1MB max) prevents memory exhaustion attacks
  - **Timeout hardening** with configurable bounds (1s min, 60s max)
  - **Sensitive data masking** in all error messages
  - **Comprehensive test coverage** - 56 test cases covering security, validation, retries, and error handling

### Added
- **API Performance Profiling** - Comprehensive endpoint performance monitoring and analysis
  - New `PerformanceProfilingMiddleware` tracks request duration per endpoint
  - Configurable slow request threshold (default: 1000ms) via `PERF_SLOW_THRESHOLD_MS`
  - Memory-efficient profile storage with configurable limit (default: 10,000 profiles)
  - NEW API Endpoints:
    - `GET /v1/performance/profiles` — View recent request profiles with optional slow-only filter
    - `GET /v1/performance/stats` — Aggregated endpoint statistics (count, avg/min/max times, slow%)
    - `GET /v1/performance/slowest` — Top N slowest endpoints by average response time
    - `GET /v1/performance/summary` — Quick performance overview
    - `DELETE /v1/performance/profiles` — Clear all profiles (auth required)
  - NEW CLI Commands (`mc performance`):
    - `mc performance` — Show performance summary (default)
    - `mc performance --stats` — Detailed endpoint statistics table
    - `mc performance --slowest [n]` — Show top N slowest endpoints
    - `mc performance --profiles [n]` — Show recent request profiles
    - `mc performance --profiles --slow-only` — Only show slow requests
    - `mc performance --clear` — Clear all performance profiles
  - Features:
    - Color-coded response times (green < 500ms, yellow < 1000ms, red > 1000ms)
    - Automatic logging of slow requests with warnings
    - Groups profiles by endpoint for better readability
    - Pydantic models for type-safe responses
    - OpenAPI documentation in Swagger UI and ReDoc
  - Files: `lib/performance.js` (CLI), updated `middleware.py`, `models.py`, `main.py`

- **Secrets Management Module (`mc secrets`)** - Secure, centralized secrets management for the MasterClaw ecosystem
  - `mc secrets check` — Validate all required secrets are configured across CLI and .env
  - `mc secrets list` — Display configured secrets with masking (never shows full values)
  - `mc secrets set <key> <value>` — Securely store secrets with format validation
  - `mc secrets get <key>` — Retrieve secret metadata with masked value
  - `mc secrets delete <key>` — Remove secrets with confirmation
  - `mc secrets rotate <key>` — Generate new tokens or rotate API keys
  - `mc secrets validate <key>` — Test secrets against their services (OpenAI, Anthropic, Gateway)
  - `mc secrets sync` — Synchronize secrets between CLI storage and .env file
  - `mc secrets export` — Export secrets (masked) for backup or documentation
  - Security: File permissions 0o600, masked display by default, audit logging without values
  - Validation: Enforces API key formats (OpenAI: `sk-...`, Anthropic: `sk-ant-...`)
  - Token generation: Cryptographically secure random token generation for GATEWAY_TOKEN
  - Required secrets tracking: GATEWAY_TOKEN (required), OPENAI_API_KEY, ANTHROPIC_API_KEY (optional)
  - New `lib/secrets.js` module with comprehensive test suite (`tests/secrets.test.js`)
- **Correlation ID System** - Distributed tracing for CLI operations
  - Unique correlation IDs generated for each command execution
  - IDs propagated through logger, audit log, and event systems
  - Environment variable `MC_CORRELATION_ID` for CI/CD integration
  - HTTP header `x-correlation-id` support for API calls
  - Child correlation IDs for sub-operations (hierarchical tracing)
  - Security: IDs validated and sanitized to prevent injection
  - New `lib/correlation.js` module with 66 comprehensive tests
  - `wrapCommandWithCorrelation()` for automatic command tracing
  - Enables end-to-end tracing of operations across log types
- **Event Tracking System (`mc events`)** - Centralized event tracking and notification history
  - `mc events list` — List events with filtering by type, severity, source, and time
  - `mc events show <id>` — Display detailed event information
  - `mc events ack <id>` — Acknowledge individual events
  - `mc events ack-all` — Bulk acknowledge events
  - `mc events stats` — Event statistics and summaries
  - `mc events add <title>` — Add custom events
  - `mc events export` — Export events to JSON or CSV
  - `mc events watch` — Real-time event monitoring
  - Event types: backup, deploy, alert, error, warning, info, security, maintenance, restore, update
  - Severity levels: critical, high, medium, low, info
  - Automatic event creation from other commands (backup, deploy, restore)
- **Error Handler JSON Output Mode** - Structured JSON error output for production/CI environments
  - Set `MC_JSON_OUTPUT=1` to enable machine-readable error output
  - Structured JSON schema with timestamp, category, exit code, message, and error details
  - Sensitive data automatically masked in JSON output
  - Useful for log aggregation (ELK, Splunk, cloud logging) and CI/CD pipelines
  - Global error handlers (unhandled rejections, uncaught exceptions) also support JSON mode
- **Chat Command Security Hardening** - Enhanced security for `mc chat` command
  - Input validation: max length (10,000 chars), line count limits, dangerous pattern detection
  - XSS protection: blocks script tags, event handlers, javascript: URLs, data:text/html
  - Input sanitization: removes control characters, ANSI escapes, suspicious Unicode
  - Rate limiting: 20 messages per minute per user
  - Sensitive data masking for audit logs
  - New `lib/chat-security.js` module with comprehensive security utilities
  - 55 test cases covering validation, sanitization, and risk analysis
- **Config Command Module (`mc config`)** - Complete configuration management for CLI
  - `mc config list` — Display all configuration values with security masking
  - `mc config get <key>` — Retrieve specific values using dot notation
  - `mc config set <key> <value>` — Update configuration with type inference
  - `mc config export [file]` — Export config to JSON with sensitive value masking
  - `mc config import <file>` — Import config with diff preview and dry-run support
  - `mc config reset` — Reset to defaults with confirmation protection
  - Security features: rate limiting, sensitive value masking, prototype pollution protection
- **Security Auto-Responder Path Fallback** - Improved error handling for file system operations
  - Automatic fallback to alternate paths when default paths aren't writable
  - Graceful handling of permission errors with informative logging
  - Path information included in statistics for better observability
  - System continues to function in-memory when persistence fails
  - New tests for permission error scenarios
- **Batch Memory Import/Export API** - Efficient bulk memory operations
  - `POST /v1/memory/batch` - Import up to 1000 memories in a single request
    - Skip duplicate detection based on content hash
    - Source prefix for tracking import origin
    - Detailed import report with success/failure counts
  - `POST /v1/memory/export` - Export memories with flexible filtering
    - Semantic search query filtering
    - Metadata, source, and date range filters
    - Up to 5000 memories per export request
  - New Pydantic models: `BatchMemoryImportRequest`, `BatchMemoryImportResponse`, `MemoryExportRequest`, `MemoryExportResponse`
  - Complements existing single-memory endpoints for migration and backup workflows
- **Tool Use Framework** - Comprehensive tool calling system for AI agents
  - `GET /v1/tools` - List all available tools with their definitions
  - `GET /v1/tools/{tool_name}` - Get detailed information about a specific tool
  - `POST /v1/tools/execute` - Execute a tool with provided parameters
  - `GET /v1/tools/definitions/openai` - Get tools in OpenAI function format
  - **GitHub Tool** - Full GitHub API integration (repos, issues, PRs, comments)
  - **System Tool** - Safe system commands and information (with security restrictions)
  - **Weather Tool** - Weather data via Open-Meteo API (no API key required)
  - Extensible registry for adding custom tools
  - Parameter validation and type checking
  - Security controls for dangerous operations
- **Interactive API Documentation** - Auto-generated docs with Swagger UI and ReDoc
  - Swagger UI at `/docs` - Interactive API explorer with "Try it out" feature
  - ReDoc at `/redoc` - Clean, responsive API reference documentation  
  - OpenAPI 3.0 schema at `/openapi.json` - Machine-readable specification
  - Categorized endpoints with descriptions for better navigation
  - Enhanced root endpoint (`/`) with documentation URLs
- **Analytics API Endpoints** - Expose usage metrics and statistics
  - `GET /v1/analytics` - Analytics system summary and available metrics
  - `GET/POST /v1/analytics/stats` - Usage statistics (requests, chats, tokens, error rates)
  - Automatic tracking of API requests with timing and status codes
  - Chat usage tracking by provider and model
  - Memory search performance metrics
  - Configurable lookback period (1-90 days)
- **WebSocket Streaming Chat Endpoint** (`/v1/chat/stream/{session_id}`)
  - Real-time token-by-token streaming for chat responses
  - Support for both OpenAI and Anthropic providers
  - Integrated memory retrieval for contextual responses
  - Comprehensive error handling with typed error codes
  - Automatic conversation storage to memory
  - Bidirectional JSON message protocol

### Changed
- Updated root endpoint (`/`) to include new WebSocket and Analytics endpoints
- Chat and memory endpoints now track analytics automatically
- Enhanced API metadata with detailed descriptions and authentication info
- **Security**: Improved `security_response.py` with graceful file permission error handling
  - Added `_ensure_writable_path()` method with automatic fallback logic
  - Enhanced `_save_blocklist()` and `_save_rules()` with specific error handling
  - Updated `get_stats()` to include path information for debugging

## [0.1.0] - 2026-02-13

### Added
- Initial release of MasterClaw Core
- REST API with chat completion endpoint (`/v1/chat`)
- Memory management with semantic search
- WebSocket connection manager (infrastructure only)
- Support for OpenAI and Anthropic LLM providers
- Health check endpoint (`/health`)

---

*Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)*
