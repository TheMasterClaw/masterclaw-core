# Troubleshooting Guide and Diagnostic Assistant Improvement Summary

## Overview
Added `mc troubleshoot` command to provide interactive troubleshooting for common MasterClaw issues, helping users diagnose and fix problems without searching documentation.

## Problem
When users encountered issues with MasterClaw, they had to:
- Search through documentation manually
- Figure out which commands to run for diagnosis
- Guess at solutions without guidance
- Spend time on trial and error

## Solution
Created an interactive troubleshooting assistant with 8 common issues:

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

### Commands

```bash
mc troubleshoot wizard              # Interactive troubleshooting wizard
mc troubleshoot list                # List all common issues
mc troubleshoot list --category docker
mc troubleshoot list --severity critical
mc troubleshoot guide services-down # Show detailed guide
mc troubleshoot diagnose            # Quick diagnostic checks
```

### Features

1. **Interactive Wizard**: Step-by-step diagnosis with prompts
2. **Symptom Matching**: Users select their symptoms to identify issues
3. **Solution Commands**: One-click execution of fixes
4. **Diagnosis Steps**: Guided diagnostics before attempting fixes
5. **Prevention Tips**: Learn how to avoid issues in the future
6. **Category/Severity Filters**: Focus on specific problem types

### Issue Structure

Each issue includes:
- **Title**: Clear name of the problem
- **Symptoms**: Observable behaviors
- **Severity**: Critical/High/Medium/Low
- **Category**: Docker/SSL/Performance/Database/API/Backup/Notifications
- **Diagnosis**: Steps to confirm the issue
- **Solutions**: Multiple solutions with commands
- **Prevention**: Tips to avoid recurrence

## Files Modified

1. **`masterclaw-tools/lib/troubleshoot.js`** (NEW, ~600 lines)
   - Issue database with 8 common problems
   - Interactive wizard with inquirer
   - Solution command execution
   - Diagnostic functions

2. **`masterclaw-tools/bin/mc.js`**
   - Added import for troubleshoot module
   - Registered `troubleshootCmd`
   - Updated version to 0.56.0

3. **`masterclaw-tools/package.json`**
   - Bumped version to 0.56.0

4. **`masterclaw-tools/README.md`**
   - Added comprehensive documentation section

5. **`CHANGELOG.md`**
   - Added detailed changelog entry

6. **`ECOSYSTEM_SUMMARY.md`**
   - Updated key files list
   - Added commands to CLI reference

## Example Workflow

### Interactive Wizard
```bash
$ mc troubleshoot wizard

🐾 MasterClaw Troubleshooting Wizard
──────────────────────────────────────────────────

? What area are you having issues with? docker
? Which issue matches your problem? Services Not Starting 🔴 CRITICAL

Services Not Starting
──────────────────────────────────────────────────

Symptoms:
  • Docker containers keep restarting
  • mc status shows services as down
  • Cannot access the web interface

Diagnosis Steps:
  1. Check Docker daemon: docker ps
  2. View service logs: mc logs <service>
  3. Check port conflicts: lsof -i :80, :443

Suggested Solutions:
? Which solution would you like to try?
  ❯ Restart all services - Restart MasterClaw services
    Command: mc revive
```

### Direct Guide Access
```bash
$ mc troubleshoot guide ssl-cert-issues

🐾 SSL Certificate Problems
──────────────────────────────────────────────────

Severity: 🔴 HIGH
Category: ssl

Symptoms:
  • Browser shows certificate warning
  • HTTPS not working
  • Traefik shows certificate errors

Diagnosis Steps:
  1. Check certificate status: mc ssl check
  2. Verify domain DNS: nslookup <domain>
  3. Check Traefik logs: mc logs traefik

Solutions:
  1. Force SSL renewal
     Force certificate renewal
     Command: mc ssl renew

  2. Check DNS configuration
     Ensure domain points to this server
     Command: nslookup $(grep DOMAIN .env | cut -d= -f2)

Prevention:
  • Enable SSL monitoring: mc ssl monitor --install
  • Set up expiration alerts
  • Test SSL regularly with mc ssl check
```

### Quick Diagnostics
```bash
$ mc troubleshoot diagnose

🐾 Running Quick Diagnostics
──────────────────────────────────────────────────

Docker daemon        ✅ OK
MasterClaw status    ❌ Failed
Disk space           ✅ OK
Memory usage         ✅ OK

Run: mc troubleshoot wizard for guided help
```

## Benefits

1. **Faster Resolution**: Users get guided solutions immediately
2. **Reduced Support Burden**: Self-service troubleshooting
3. **Better UX**: No need to search documentation
4. **Learning**: Prevention tips help users avoid issues
5. **Consistency**: Standardized diagnosis and solutions

## Testing
- Module loads successfully
- All 8 issues accessible
- Interactive prompts work correctly
- Command execution functional
- Filters work properly

## Version
- CLI Version: 0.56.0
- Feature: Troubleshooting Guide and Diagnostic Assistant
