# Memory Protocol for Master Claw

## Problem
Context is lost between sessions and sometimes within sessions because memory isn't being updated frequently enough. This creates frustration when I don't remember what we were working on.

## Solution: Frequent Memory Updates

### When to Update Memory

**IMMEDIATE (write to memory during the conversation):**
- [ ] New projects initiated
- [ ] Key decisions made
- [ ] Action items assigned
- [ ] Important context shared
- [ ] Bug fixes or workarounds discovered
- [ ] Deployment/deployment issues
- [ ] New tools or integrations mentioned

**END OF SESSION (summary):**
- [ ] Summary of all work completed
- [ ] Outstanding tasks
- [ ] Next steps
- [ ] Any blockers or issues

### Memory File Structure

**Daily Log: `memory/YYYY-MM-DD.md`**
- Raw, chronological notes of what happened
- Quick captures during work
- Technical details, commands, errors

**Long-term: `MEMORY.md`**
- Curated important information
- Ongoing projects status
- Lessons learned
- System architecture decisions

### Template for Daily Log

```markdown
# 2026-MM-DD - Session Log

## Active Projects
- Project Name: Brief status

## Conversation Summary
### [Time] - Topic
- Key points
- Decisions made
- Action items

## Technical Details
- Commands used
- Configs changed
- Issues encountered

## Next Steps
- [ ] Task 1
- [ ] Task 2
```

## Protocol Enforcement

**During conversation:**
1. When user mentions a new project → Write to memory immediately
2. When user references something "we made earlier" → Search memory + document if missing
3. Every 30 minutes of active work → Quick memory checkpoint

**End of session:**
1. Summarize all work done
2. Update MEMORY.md with important items
3. Note any follow-up tasks

---
*Created: 2026-03-18*
*Purpose: Never lose context again*
