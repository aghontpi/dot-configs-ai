---
name: memory
description: |
  Persistent memory system that lets the AI remember user preferences, corrections, project context, and decisions across conversations.
  WHEN TO USE: Use this skill at the START of every conversation to load existing memories. Use it DURING a conversation whenever the user corrects you, expresses a preference, makes a decision, or says "remember this." Use it whenever the user asks "do you remember", "what did we decide", or "search your memory." Use it at the END of a conversation to store any new learnings. This skill should trigger on any mention of remembering, forgetting, recalling, preferences, or past decisions.
---

# Memory

A persistent memory system stored at `~/.skill-memory/`. It allows you to learn from the user over time — remembering their preferences, your past mistakes, project context, and key decisions — so every future conversation starts smarter.

## Why This Matters

Without memory, every conversation starts from scratch. The user has to repeat preferences, re-explain project context, and watch you make the same mistakes. This skill fixes that by giving you a simple, file-based memory store that persists across sessions.

## When to Use Each Script

All scripts live in `skills/memory/scripts/` and require only Python 3 (zero external dependencies).

### 1. First-Time Setup — `memory.init.py`

Run this once, or if `~/.skill-memory/` doesn't exist. It creates the directory structure safely (idempotent).

```bash
python3 skills/memory/scripts/memory.init.py
```

### 2. Storing a Memory — `memory.store.py`

Use this whenever you learn something worth remembering. Four types:

| Type | When to use | File |
|------|------------|------|
| `preference` | User expresses how they like things done | `preferences.md` |
| `correction` | User corrects a mistake you made | `corrections.md` |
| `project` | Context about a specific project | `projects/<name>.md` |
| `general` | Anything else worth remembering | `general.md` |

```bash
python3 skills/memory/scripts/memory.store.py \
  --type preference \
  --title "Uses pnpm" \
  --tags "pnpm,tooling,package-manager" \
  --content "User prefers pnpm over npm for all package management tasks."
```

```bash
python3 skills/memory/scripts/memory.store.py \
  --type correction \
  --title "Don't over-engineer solutions" \
  --tags "style,approach" \
  --content "When proposing solutions, keep them simple. User rejected overly complex script-heavy approaches in favor of lean, practical ones."
```

```bash
python3 skills/memory/scripts/memory.store.py \
  --type project \
  --project "pomodoro-app" \
  --title "Tech stack" \
  --tags "swift,macos,menubar" \
  --content "Native macOS app built with Swift. Features: floating overlay, menu bar timer, translucency controls."
```

### 3. Searching Memories — `memory.search.py`

Use this when the user asks you to recall something, or when you need to check if you already know something relevant. Supports combining filters.

```bash
# Free-text keyword search
python3 skills/memory/scripts/memory.search.py --query "pnpm"

# Filter by tags
python3 skills/memory/scripts/memory.search.py --tags "git,workflow"

# Filter by project
python3 skills/memory/scripts/memory.search.py --project "pomodoro-app"

# Filter by type
python3 skills/memory/scripts/memory.search.py --type correction

# Combined filters
python3 skills/memory/scripts/memory.search.py --query "overlay" --project "pomodoro-app" --tags "swift"
```

Results are ranked by relevance (title matches score highest, then tag matches, then content matches).

### 4. Reading Memories — `memory.read.py`

Use this at the start of conversations to load context.

```bash
# Quick overview — titles and tags only (use this at conversation start)
python3 skills/memory/scripts/memory.read.py --summary

# Full dump of everything
python3 skills/memory/scripts/memory.read.py --all

# Load a specific project's context
python3 skills/memory/scripts/memory.read.py --project pomodoro-app

# Show the 5 most recent memories
python3 skills/memory/scripts/memory.read.py --recent 5
```

## Behavioral Rules

These are the rules that govern when and how you should interact with the memory system:

### At Conversation Start
1. Check if `~/.skill-memory/` exists. If not, run `memory.init.py`.
2. Run `memory.read.py --summary` to see what you already know.
3. If you can identify the current project (from workspace path or user context), also run `memory.read.py --project <name>`.

### During the Conversation
Watch for these signals and store memories proactively:

- **User corrects you** → Store as `correction`. Example: "No, don't use npm" → store that they use pnpm.
- **User expresses a preference** → Store as `preference`. Example: "I like dark mode" or "always use TypeScript".
- **User makes a project decision** → Store as `project`. Example: "We're switching from REST to GraphQL".
- **User explicitly says "remember this"** → Store whatever they said.
- **You discover something important** → Store as `general`. Example: The user's repo uses a non-standard build system.

### When User Asks to Recall
If the user says "do you remember...", "what did we decide about...", or "search your memory for..." → run `memory.search.py` with the appropriate query.

### At Conversation End
Reflect on the conversation. If there were corrections, preferences, or decisions that weren't captured during the conversation, store them now before the conversation ends.

## Storage Format

Each memory entry follows this structure inside the markdown files:

```markdown
### [Short descriptive title]
- **Date**: 2026-03-29
- **Tags**: `tag1`, `tag2`, `tag3`
- **Memory**: [What to remember — be specific and actionable]
```

### Tagging Best Practices
- Use lowercase, hyphenated tags: `package-manager`, `code-style`, `macos`
- Include the tool/tech name: `pnpm`, `swift`, `hugo`
- Include the category: `preference`, `workflow`, `architecture`
- Keep tags to 3-5 per entry — enough to be findable, not so many they're noise
