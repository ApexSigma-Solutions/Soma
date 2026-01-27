---
name: skill-generator
description: Generates well-structured Agent Skill documents following Claude Code best practices. Use when asked to create new Agent Skills, draft SKILL.md files, or design skill architectures.
allowed-tools: Write, Read
---

# Skill Generator

## Core Principles

When generating Agent Skills, always follow these fundamental principles:

1. **Purpose-First Design**: Every Skill must solve a specific, well-defined problem
2. **Progressive Disclosure**: Keep `SKILL.md` focused (under 500 lines); move detailed content to supporting files
3. **Semantic Matching**: Write descriptions that trigger naturally based on user language
4. **Zero-Context Execution**: Bundle utility scripts that run without loading their contents

## Standard Skill Structure

### Required Frontmatter

Every `SKILL.md` MUST include:

```yaml
---
name: lowercase-hyphens-only  # max 64 chars, matches directory name
description: What it does AND when to use it. Include specific trigger terms.  # max 1024 chars
allowed-tools: Tool1, Tool2  # optional: restricts tools when skill is active
model: model-name  # optional: overrides conversation model
---
```
