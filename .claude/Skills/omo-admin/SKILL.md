---
name: omo-admin
description: Complete Oh-My-OpenCode plugin administration. Install, configure, update, diagnose, and maintain the oh-my-opencode plugin. Handles agent orchestration, model configuration, hooks, MCPs, categories, LSP setup, and troubleshooting. Triggers on 'configure omo', 'install oh-my-opencode', 'update omo config', 'diagnose omo', 'omo settings', 'oh my opencode', or any plugin administration task.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebFetch, Question, TodoWrite, TodoRead
---

# Oh-My-OpenCode Administrator

Complete configuration and maintenance toolkit for the oh-my-opencode plugin.

## When to Use This Skill

Use this skill when the user needs to:
- **Install** oh-my-opencode plugin from scratch
- **Configure** agents, categories, models, hooks, or MCPs
- **Update** existing configuration settings
- **Diagnose** issues with plugin setup or behavior
- **Maintain** plugin version updates and health checks
- **Troubleshoot** model resolution, provider issues, or runtime errors
- **Optimize** performance settings (background tasks, tmux, LSP)

**Trigger Phrases**: "configure omo", "install oh-my-opencode", "setup sisyphus", "update omo config", "diagnose plugin", "fix oh-my-opencode", "omo settings", "oh my opencode admin"

## Core Principles

### 1. Progressive Configuration
Start with minimal setup, layer complexity only when needed:
1. **Basic**: Install plugin, verify default config works
2. **Essential**: Configure available providers (Anthropic, OpenAI, Google, etc.)
3. **Optimized**: Set up categories, agent overrides, background task limits
4. **Advanced**: Tmux integration, custom agents, LSP servers, experimental features

### 2. Provider-Aware Setup
Always check available providers before configuring models:
```bash
opencode models  # List all available models/providers
```

Model resolution follows: `User Override → Provider Fallback → System Default`

### 3. JSONC First
Always use `.jsonc` format for configuration files (supports comments and trailing commas):
- User config: `~/.config/opencode/oh-my-opencode.jsonc`
- Project config: `.opencode/oh-my-opencode.jsonc`

### 4. Validate Before Apply
Always validate configuration before writing:
- Check JSON schema compliance
- Verify model availability with `opencode models`
- Test with `bunx oh-my-opencode doctor --verbose`

## Configuration File Locations

| Scope | Path | Priority |
|-------|------|----------|
| **Project** | `.opencode/oh-my-opencode.jsonc` | Higher (overrides user config) |
| **User (Windows)** | `~/.config/opencode/oh-my-opencode.jsonc` | Lower |
| **User (macOS/Linux)** | `~/.config/opencode/oh-my-opencode.jsonc` | Lower |

**Note**: `.jsonc` takes priority over `.json` if both exist.

## Installation Workflow

### Step 1: Verify Prerequisites
```bash
# Check OpenCode version (1.0.133+ recommended)
opencode --version

# Check available providers
opencode models

# Check Node.js/Bun installed
node --version || bun --version
```

### Step 2: Install Plugin
```bash
# Add plugin to OpenCode config
# Edit ~/.config/opencode/opencode.json (or opencode.jsonc)
# Add "oh-my-opencode" to the "plugin" array
```

Example:
```jsonc
{
  "plugin": [
    "oh-my-opencode"  // Add this line
  ]
}
```

### Step 3: Run Interactive Installer (Recommended)
```bash
bunx oh-my-opencode install
```

This asks about available providers and generates optimal configuration automatically.

### Step 4: Verify Installation
```bash
bunx oh-my-opencode doctor --verbose
```

Check for:
- ✅ Plugin loaded successfully
- ✅ Configuration file valid
- ✅ Model resolution working
- ✅ All required providers available

## Configuration Patterns

### Pattern 1: Minimal Setup (Just Works)
```jsonc
{
  "$schema": "https://raw.githubusercontent.com/code-yeongyu/oh-my-opencode/master/assets/oh-my-opencode.schema.json"
}
```

Uses all defaults. Good for testing.

### Pattern 2: Essential Setup (Recommended Starting Point)
```jsonc
{
  "$schema": "https://raw.githubusercontent.com/code-yeongyu/oh-my-opencode/master/assets/oh-my-opencode.schema.json",
  
  // Configure categories to use optimal models
  "categories": {
    "quick": { "model": "anthropic/claude-haiku-4-5" },  // Fast/cheap
    "visual-engineering": { "model": "google/gemini-3-pro-preview" },
    "ultrabrain": { "model": "openai/gpt-5.2-codex", "variant": "xhigh" }
  }
}
```

### Pattern 3: Power User Setup
```jsonc
{
  "$schema": "https://raw.githubusercontent.com/code-yeongyu/oh-my-opencode/master/assets/oh-my-opencode.schema.json",
  
  // Override specific agents
  "agents": {
    "oracle": { "model": "openai/gpt-5.2" },  // GPT for debugging
    "librarian": { "model": "anthropic/claude-sonnet-4-5" },
    "explore": { "model": "opencode/gpt-5-nano" },  // Free model for grep
    "Sisyphus": { 
      "model": "anthropic/claude-opus-4-5",
      "temperature": 0.3
    }
  },
  
  // Configure all categories
  "categories": {
    "quick": { "model": "anthropic/claude-haiku-4-5" },
    "visual-engineering": { 
      "model": "google/gemini-3-pro-preview",
      "prompt_append": "Use shadcn/ui components and Tailwind CSS."
    },
    "ultrabrain": { 
      "model": "openai/gpt-5.2-codex",
      "variant": "xhigh"
    },
    "writing": { "model": "google/gemini-3-flash-preview" }
  },
  
  // Background task concurrency limits
  "background_task": {
    "defaultConcurrency": 5,
    "providerConcurrency": {
      "anthropic": 3,
      "google": 10
    },
    "modelConcurrency": {
      "anthropic/claude-opus-4-5": 2
    }
  },
  
  // Git master settings
  "git_master": {
    "commit_footer": true,
    "include_co_authored_by": true
  }
}
```

### Pattern 4: Advanced Setup (All Features)
```jsonc
{
  "$schema": "https://raw.githubusercontent.com/code-yeongyu/oh-my-opencode/master/assets/oh-my-opencode.schema.json",
  
  "agents": {
    "Sisyphus": {
      "model": "anthropic/claude-opus-4-5",
      "temperature": 0.3
    },
    "oracle": { "model": "openai/gpt-5.2" },
    "librarian": { 
      "model": "anthropic/claude-sonnet-4-5",
      "prompt_append": "Always use context7 for official docs."
    },
    "explore": { "model": "anthropic/claude-haiku-4-5" }
  },
  
  "categories": {
    "quick": { "model": "anthropic/claude-haiku-4-5" },
    "visual-engineering": { "model": "google/gemini-3-pro-preview" },
    "ultrabrain": { 
      "model": "openai/gpt-5.2-codex",
      "variant": "xhigh"
    },
    "artistry": { 
      "model": "google/gemini-3-pro-preview",
      "variant": "max"
    },
    "writing": { "model": "google/gemini-3-flash-preview" }
  },
  
  "background_task": {
    "defaultConcurrency": 5,
    "providerConcurrency": {
      "anthropic": 3,
      "openai": 5,
      "google": 10
    }
  },
  
  "tmux": {
    "enabled": true,
    "layout": "main-vertical",
    "main_pane_size": 60
  },
  
  "git_master": {
    "commit_footer": true,
    "include_co_authored_by": true
  },
  
  "browser_automation_engine": {
    "provider": "playwright"  // or "agent-browser"
  },
  
  "sisyphus_agent": {
    "disabled": false,
    "default_builder_enabled": false,
    "planner_enabled": true,
    "replace_plan": true
  },
  
  "disabled_hooks": [
    // Uncomment to disable specific hooks
    // "comment-checker",
    // "todo-continuation-enforcer"
  ],
  
  "disabled_mcps": [
    // Uncomment to disable specific MCPs
    // "websearch",
    // "context7"
  ],
  
  "experimental": {
    "truncate_all_tool_outputs": false,
    "aggressive_truncation": false,
    "auto_resume": false
  }
}
```

## Common Configuration Tasks

### Task: Configure Available Providers
```javascript
// Step 1: Check available models
await bash("opencode models");

// Step 2: Update categories based on available providers
const config = {
  "categories": {
    // Only configure categories for models you have access to
    "quick": { "model": "anthropic/claude-haiku-4-5" },  // If Anthropic available
    "visual-engineering": { "model": "google/gemini-3-pro-preview" }  // If Google available
  }
};

// Step 3: Write to config file
await writeConfig("~/.config/opencode/oh-my-opencode.jsonc", config);

// Step 4: Verify
await bash("bunx oh-my-opencode doctor --verbose");
```

### Task: Override Specific Agent Model
```jsonc
{
  "agents": {
    "oracle": {
      "model": "openai/gpt-5.2",  // Change from default
      "temperature": 0.5,
      "prompt_append": "Focus on architectural patterns and debugging."
    }
  }
}
```

### Task: Disable Unwanted Features
```jsonc
{
  "disabled_agents": ["multimodal-looker"],  // Disable specific agents
  "disabled_skills": ["playwright"],  // Disable browser automation
  "disabled_hooks": ["comment-checker", "agent-usage-reminder"],
  "disabled_mcps": ["websearch"]  // Disable web search MCP
}
```

### Task: Set Up Background Task Limits
```jsonc
{
  "background_task": {
    "defaultConcurrency": 5,  // Max 5 concurrent background tasks
    "providerConcurrency": {
      "anthropic": 3,  // Max 3 concurrent Anthropic tasks (rate limits)
      "google": 10  // Max 10 concurrent Google tasks (higher limits)
    },
    "modelConcurrency": {
      "anthropic/claude-opus-4-5": 2  // Max 2 concurrent Opus (expensive)
    }
  }
}
```

### Task: Enable Tmux Integration
```jsonc
{
  "tmux": {
    "enabled": true,
    "layout": "main-vertical",  // Main pane left, agents stacked right
    "main_pane_size": 60,  // Main pane takes 60% width
    "main_pane_min_width": 120,
    "agent_pane_min_width": 40
  }
}
```

**Note**: Requires running inside tmux with `opencode --port 4096`

### Task: Add Custom LSP Server
```jsonc
{
  "lsp": {
    "typescript-language-server": {
      "command": ["typescript-language-server", "--stdio"],
      "extensions": [".ts", ".tsx"],
      "priority": 10
    },
    "python-lsp-server": {
      "command": ["pylsp"],
      "extensions": [".py"],
      "env": {
        "PYTHONPATH": "/custom/path"
      }
    }
  }
}
```

## Diagnostic Commands

### Check Plugin Health
```bash
bunx oh-my-opencode doctor --verbose
```

**What it checks**:
- ✅ Plugin loaded in OpenCode config
- ✅ Configuration file valid (JSON schema)
- ✅ Model resolution for all agents/categories
- ✅ Provider availability
- ✅ Hook/MCP/Agent status

### View Effective Configuration
```bash
# Read current config
cat ~/.config/opencode/oh-my-opencode.jsonc

# Or for project config
cat .opencode/oh-my-opencode.jsonc
```

### Test Model Availability
```bash
opencode models | grep -i "claude"  # Check Anthropic models
opencode models | grep -i "gemini"  # Check Google models
opencode models | grep -i "gpt"  # Check OpenAI models
```

### Debug Model Resolution
```bash
bunx oh-my-opencode doctor --verbose
```

Look for "Model Resolution" section showing:
- User overrides
- Provider fallback chains
- Effective resolved models

## Troubleshooting Guide

### Issue: Plugin Not Loading

**Symptoms**: oh-my-opencode features don't work

**Diagnosis**:
```bash
# Check OpenCode config
cat ~/.config/opencode/opencode.json | grep "oh-my-opencode"

# Check plugin installation
bunx oh-my-opencode --version
```

**Fix**:
```jsonc
// Edit ~/.config/opencode/opencode.json
{
  "plugin": [
    "oh-my-opencode"  // Ensure this is present
  ]
}
```

### Issue: Model Not Available

**Symptoms**: "Model not found" or agent falls back to default

**Diagnosis**:
```bash
# Check available models
opencode models

# Check model resolution
bunx oh-my-opencode doctor --verbose
```

**Fix**: Update config to use available models or add provider:
```jsonc
{
  "agents": {
    "oracle": {
      "model": "anthropic/claude-sonnet-4-5"  // Use available model
    }
  }
}
```

### Issue: Categories Using Wrong Models

**Symptoms**: All tasks use system default model instead of category-specific models

**Diagnosis**: Categories not configured in oh-my-opencode.json

**Fix**: Add categories to config:
```jsonc
{
  "categories": {
    "quick": { "model": "anthropic/claude-haiku-4-5" },
    "visual-engineering": { "model": "google/gemini-3-pro-preview" }
  }
}
```

**Explanation**: Model resolution priority is:
1. User override (in config)
2. Category built-in default (only if category in config)
3. System default (opencode.json)

Without config, **all categories fall back to system default**.

### Issue: Background Tasks Not Running

**Symptoms**: Delegate tasks don't spawn or all run sequentially

**Diagnosis**:
```bash
# Check concurrency config
cat ~/.config/opencode/oh-my-opencode.jsonc | grep -A 10 "background_task"
```

**Fix**: Increase concurrency limits:
```jsonc
{
  "background_task": {
    "defaultConcurrency": 5,  // Increase from 1
    "providerConcurrency": {
      "anthropic": 3
    }
  }
}
```

### Issue: Tmux Integration Not Working

**Symptoms**: Background agents don't appear in tmux panes

**Diagnosis**:
```bash
# Check if inside tmux
echo $TMUX  # Should output path if inside tmux

# Check if OpenCode running with --port
ps aux | grep "opencode.*--port"

# Check tmux config
cat ~/.config/opencode/oh-my-opencode.jsonc | grep -A 5 "tmux"
```

**Fix**:
1. Ensure running inside tmux: `tmux new -s dev`
2. Start OpenCode with port: `opencode --port 4096`
3. Enable in config:
```jsonc
{
  "tmux": {
    "enabled": true
  }
}
```

### Issue: JSON Parsing Errors

**Symptoms**: "Invalid JSON" or config not loading

**Diagnosis**:
```bash
# Validate JSON syntax
jq . ~/.config/opencode/oh-my-opencode.jsonc
# Or
bunx oh-my-opencode doctor
```

**Common Causes**:
- Missing commas between properties
- Trailing comma after last property (OK in JSONC)
- Unclosed brackets/braces
- Invalid escape sequences

**Fix**: Use JSONC format (allows comments and trailing commas):
```jsonc
{
  // Comments are OK in JSONC
  "agents": {
    "oracle": { "model": "openai/gpt-5.2" },  // Trailing comma OK
  },  // This trailing comma is also OK
}
```

## Model Resolution System

### How It Works

At runtime, oh-my-opencode resolves models using a 3-step process:

```
Step 1: USER OVERRIDE
  ↓ User specified model in config?
  ✓ YES → Use exactly as specified
  ✗ NO  → Continue to Step 2

Step 2: PROVIDER PRIORITY FALLBACK
  ↓ For each provider in requirement.providers order:
  ↓ Try: anthropic/claude-opus-4-5
  ↓ Try: github-copilot/claude-opus-4-5
  ↓ Try: opencode/claude-opus-4-5
  ✓ Found? → Return matched model
  ✗ Not found? → Try next provider

Step 3: SYSTEM DEFAULT
  ↓ All providers exhausted?
  → Return systemDefaultModel (from opencode.json)
```

### Agent Provider Chains

| Agent | Default Model | Provider Priority |
|-------|---------------|-------------------|
| Sisyphus | claude-opus-4-5 | anthropic → github-copilot → opencode → antigravity → google |
| oracle | gpt-5.2 | openai → anthropic → google → github-copilot → opencode |
| librarian | big-pickle | opencode → github-copilot → anthropic |
| explore | gpt-5-nano | anthropic → opencode |
| multimodal-looker | gemini-3-flash | google → openai → zai-coding-plan → anthropic → opencode |

### Category Provider Chains

| Category | Default Model | Provider Priority |
|----------|---------------|-------------------|
| visual-engineering | gemini-3-pro | google → openai → anthropic → github-copilot → opencode |
| ultrabrain | gpt-5.2-codex | openai → anthropic → google → github-copilot → opencode |
| quick | claude-haiku-4-5 | anthropic → github-copilot → opencode → antigravity → google |
| writing | gemini-3-flash | google → openai → anthropic → github-copilot → opencode |

### Override Examples

**Override single agent**:
```jsonc
{
  "agents": {
    "Sisyphus": {
      "model": "anthropic/claude-sonnet-4-5"  // Skip provider chain, use this
    }
  }
}
```

**Override category**:
```jsonc
{
  "categories": {
    "visual-engineering": {
      "model": "anthropic/claude-opus-4-5"  // Use Anthropic instead of Google
    }
  }
}
```

## Advanced Features

### Custom Categories

Create domain-specific task delegation:

```jsonc
{
  "categories": {
    "data-science": {
      "model": "anthropic/claude-sonnet-4-5",
      "temperature": 0.2,
      "prompt_append": "Focus on pandas, numpy, scikit-learn. Use type hints."
    },
    "devops": {
      "model": "openai/gpt-5.2",
      "prompt_append": "Prefer Docker, k8s, terraform. Follow 12-factor app."
    }
  }
}
```

**Usage**:
```javascript
delegate_task(category="data-science", prompt="Build ETL pipeline for CSV data")
delegate_task(category="devops", prompt="Create Dockerfile for Node.js app")
```

### Agent Permissions

Fine-grained control over agent capabilities:

```jsonc
{
  "agents": {
    "explore": {
      "permission": {
        "edit": "deny",  // Read-only agent
        "bash": {
          "git": "allow",  // Only allow git commands
          "rm": "deny"
        },
        "webfetch": "allow"
      }
    },
    "oracle": {
      "permission": {
        "edit": "ask",  // Prompt before editing
        "bash": "allow",
        "external_directory": "deny"  // Stay in project
      }
    }
  }
}
```

### Browser Automation Switching

Choose between playwright (default) and agent-browser:

**Playwright (MCP Tools)**:
```jsonc
{
  "browser_automation_engine": {
    "provider": "playwright"
  }
}
```

**agent-browser (CLI)**:
```jsonc
{
  "browser_automation_engine": {
    "provider": "agent-browser"
  }
}
```

**Note**: agent-browser requires manual installation:
```bash
bun add -g agent-browser
agent-browser install
```

### Experimental Features

Opt-in cutting-edge features:

```jsonc
{
  "experimental": {
    "truncate_all_tool_outputs": true,  // Truncate all tools, not just grep/glob
    "aggressive_truncation": true,  // Aggressively truncate on token limits
    "auto_resume": false  // Auto-resume after thinking block errors
  }
}
```

**Warning**: May cause unexpected behavior. Use with caution.

## Best Practices

### 1. Start Minimal, Add Incrementally
Don't configure everything at once. Start with defaults, identify bottlenecks, then optimize.

**Good**:
```jsonc
// Week 1: Defaults
{}

// Week 2: Add category overrides for available providers
{
  "categories": {
    "quick": { "model": "anthropic/claude-haiku-4-5" }
  }
}

// Week 3: Fine-tune agents based on usage
{
  "agents": {
    "oracle": { "model": "openai/gpt-5.2" }
  }
}
```

**Bad**:
```jsonc
// Day 1: Configure everything without understanding
{
  "agents": { /* 20 agent overrides */ },
  "categories": { /* all 7 categories */ },
  "background_task": { /* complex concurrency */ },
  "experimental": { "truncate_all_tool_outputs": true }
}
```

### 2. Use JSONC for Maintainability
Always use `.jsonc` extension and add comments explaining non-obvious choices:

```jsonc
{
  // Use GPT for oracle because it excels at architectural reasoning
  "agents": {
    "oracle": { "model": "openai/gpt-5.2" }
  },
  
  // Limit Opus concurrency to control costs
  "background_task": {
    "modelConcurrency": {
      "anthropic/claude-opus-4-5": 2  // Max 2 concurrent ($15/MTok)
    }
  }
}
```

### 3. Validate After Every Change
Always run doctor after config changes:

```bash
# Edit config
vim ~/.config/opencode/oh-my-opencode.jsonc

# Validate
bunx oh-my-opencode doctor --verbose

# Test in OpenCode
opencode
```

### 4. Use Categories for Common Patterns
Don't override agents directly for common tasks. Use categories:

**Good**:
```jsonc
{
  "categories": {
    "quick": { "model": "anthropic/claude-haiku-4-5" }  // For all trivial tasks
  }
}
```

**Usage**:
```javascript
delegate_task(category="quick", prompt="Fix this typo")
delegate_task(category="quick", prompt="Add this import")
```

**Bad**:
```jsonc
{
  "agents": {
    "Sisyphus-Junior": { "model": "anthropic/claude-haiku-4-5" }  // Affects ALL delegate_task calls
  }
}
```

### 5. Monitor Background Task Limits
Start conservative, increase based on observation:

```jsonc
{
  "background_task": {
    "defaultConcurrency": 3,  // Start low
    "providerConcurrency": {
      "anthropic": 2  // Anthropic has strict rate limits
    }
  }
}
```

Watch for:
- Rate limit errors → Decrease concurrency
- Tasks queuing slowly → Increase concurrency
- High costs → Add modelConcurrency limits for expensive models

### 6. Document Custom Configurations
For project configs, add README explaining choices:

```markdown
# .opencode/oh-my-opencode.jsonc

This project uses:
- **oracle (GPT-5.2)**: Our backend is complex TypeScript, GPT excels here
- **visual-engineering (Gemini)**: React components, Gemini better for UI
- **quick (Haiku)**: Fast iteration on trivial changes
- **Background limit: 3**: Our Anthropic tier limits to 5 concurrent
```

## Configuration Schema Reference

Full schema available at:
```
https://raw.githubusercontent.com/code-yeongyu/oh-my-opencode/master/assets/oh-my-opencode.schema.json
```

**Top-level properties**:
- `agents`: Override agent settings (model, temperature, permissions, etc.)
- `categories`: Configure task delegation categories
- `background_task`: Concurrency limits for parallel agents
- `tmux`: Tmux integration settings
- `git_master`: Git commit behavior
- `browser_automation_engine`: Browser automation provider
- `sisyphus_agent`: Sisyphus orchestrator settings
- `disabled_agents`: Array of agents to disable
- `disabled_skills`: Array of skills to disable
- `disabled_hooks`: Array of hooks to disable
- `disabled_mcps`: Array of MCPs to disable
- `lsp`: LSP server configurations
- `experimental`: Experimental feature flags

**Agent/Category properties**:
- `model`: Model identifier (e.g., "anthropic/claude-opus-4-5")
- `temperature`: Sampling temperature (0.0-1.0)
- `top_p`: Nucleus sampling (0.0-1.0)
- `maxTokens`: Max output tokens
- `thinking`: Enable thinking mode
- `reasoningEffort`: Reasoning effort level
- `textVerbosity`: Text verbosity level
- `variant`: Model variant (low/medium/high/xhigh/max)
- `prompt_append`: Additional instructions
- `tools`: Allowed tools array
- `permission`: Permission overrides
- `disable`: Disable this agent/category

## Quick Reference

### Essential Commands
```bash
# Install plugin
bunx oh-my-opencode install

# Check health
bunx oh-my-opencode doctor --verbose

# List available models
opencode models

# View version
bunx oh-my-opencode --version

# Update plugin
bun update oh-my-opencode
```

### Config File Paths
```bash
# User config
~/.config/opencode/oh-my-opencode.jsonc

# Project config (higher priority)
.opencode/oh-my-opencode.jsonc

# OpenCode main config
~/.config/opencode/opencode.json
```

### Default Agents
- **Sisyphus**: Main orchestrator (Claude Opus 4.5)
- **oracle**: Debugging/architecture (GPT-5.2)
- **librarian**: Docs/search (big-pickle)
- **explore**: Fast codebase grep (gpt-5-nano)
- **multimodal-looker**: Image/video analysis (gemini-3-flash)

### Default Categories
- **quick**: Trivial tasks (Haiku)
- **visual-engineering**: Frontend/UI (Gemini Pro)
- **ultrabrain**: Complex logic (GPT-5.2 Codex)
- **artistry**: Creative tasks (Gemini Pro)
- **writing**: Documentation (Gemini Flash)
- **unspecified-low**: Misc low-effort (Sonnet)
- **unspecified-high**: Misc high-effort (Opus)

### Default MCPs
- **websearch**: Exa AI web search
- **context7**: Official documentation lookup
- **grep_app**: GitHub code search

### Default Skills
- **playwright**: Browser automation (MCP)
- **git-master**: Git expertise (atomic commits, rebase)

## Workflow Examples

### Example 1: First-Time Setup

**User**: "Install and configure oh-my-opencode for my team"

**Agent Workflow**:
```javascript
// Step 1: Check prerequisites
await bash("opencode --version");
await bash("opencode models");

// Step 2: Add plugin to OpenCode config
const opencodeConfig = await read("~/.config/opencode/opencode.json");
// Edit to add "oh-my-opencode" to plugin array
await edit(...);

// Step 3: Run interactive installer
await bash("bunx oh-my-opencode install");

// Step 4: Verify installation
await bash("bunx oh-my-opencode doctor --verbose");

// Step 5: Document for team
await write(".opencode/README.md", "# Oh-My-OpenCode Setup\n...");
```

### Example 2: Optimize for Available Providers

**User**: "I have Anthropic and Google, optimize my config"

**Agent Workflow**:
```javascript
// Step 1: Check available models
const models = await bash("opencode models");

// Step 2: Identify Anthropic and Google models
// anthropic/claude-opus-4-5, anthropic/claude-sonnet-4-5, anthropic/claude-haiku-4-5
// google/gemini-3-pro-preview, google/gemini-3-flash-preview

// Step 3: Generate optimal config
const config = {
  "$schema": "https://raw.githubusercontent.com/code-yeongyu/oh-my-opencode/master/assets/oh-my-opencode.schema.json",
  "agents": {
    "Sisyphus": { "model": "anthropic/claude-opus-4-5" },
    "librarian": { "model": "anthropic/claude-sonnet-4-5" },
    "explore": { "model": "anthropic/claude-haiku-4-5" },
    "multimodal-looker": { "model": "google/gemini-3-flash-preview" }
  },
  "categories": {
    "quick": { "model": "anthropic/claude-haiku-4-5" },
    "visual-engineering": { "model": "google/gemini-3-pro-preview" },
    "writing": { "model": "google/gemini-3-flash-preview" },
    "unspecified-low": { "model": "anthropic/claude-sonnet-4-5" },
    "unspecified-high": { "model": "anthropic/claude-opus-4-5" }
  },
  "background_task": {
    "defaultConcurrency": 5,
    "providerConcurrency": {
      "anthropic": 3,  // Conservative for rate limits
      "google": 10     // Google has higher limits
    }
  }
};

// Step 4: Write config
await write("~/.config/opencode/oh-my-opencode.jsonc", JSON.stringify(config, null, 2));

// Step 5: Validate
await bash("bunx oh-my-opencode doctor --verbose");
```

### Example 3: Troubleshoot Model Resolution

**User**: "Oracle keeps using Sonnet instead of GPT-5.2"

**Agent Workflow**:
```javascript
// Step 1: Check current config
const config = await read("~/.config/opencode/oh-my-opencode.jsonc");

// Step 2: Check available models
const models = await bash("opencode models | grep -i gpt");

// Step 3: Check doctor output
const doctor = await bash("bunx oh-my-opencode doctor --verbose");

// Step 4: Diagnose
// If GPT-5.2 not in available models → Need to add OpenAI provider
// If GPT-5.2 available but oracle using Sonnet → Config override needed

// Step 5: Fix (assuming GPT available)
await edit("~/.config/opencode/oh-my-opencode.jsonc", {
  oldString: `"agents": {`,
  newString: `"agents": {
    "oracle": { "model": "openai/gpt-5.2" },`
});

// Step 6: Verify
await bash("bunx oh-my-opencode doctor --verbose");
```

### Example 4: Enable Tmux Integration

**User**: "Set up tmux so I can see background agents working"

**Agent Workflow**:
```javascript
// Step 1: Check if inside tmux
const tmux = await bash("echo $TMUX");
if (!tmux) {
  // Inform user to start tmux first
  return "Please run inside tmux session: tmux new -s dev";
}

// Step 2: Create shell function for easy startup
const shellFunction = `
# Add to ~/.config/fish/config.fish (or ~/.bashrc for bash)
function oc
    opencode --port 4096 $argv
end
`;

await write("/tmp/oc-function.fish", shellFunction);

// Step 3: Enable tmux in config
await edit("~/.config/opencode/oh-my-opencode.jsonc", {
  oldString: `{`,
  newString: `{
  "tmux": {
    "enabled": true,
    "layout": "main-vertical",
    "main_pane_size": 60
  },`
});

// Step 4: Inform user
return `
Tmux integration enabled! 

Setup:
1. Add the function from /tmp/oc-function.fish to your shell config
2. Restart shell or source the config
3. Run: oc (instead of opencode)
4. Background agents will appear in separate panes

Test with:
delegate_task(run_in_background=true, category="quick", prompt="List project files")
`;
```

## Summary

This skill provides complete administration for oh-my-opencode plugin:
- ✅ Installation and initial setup
- ✅ Configuration for all features (agents, categories, hooks, MCPs, LSP)
- ✅ Model resolution optimization based on available providers
- ✅ Diagnostic and troubleshooting workflows
- ✅ Best practices and patterns
- ✅ Advanced features (tmux, background tasks, permissions)

**When to use**: Any task involving oh-my-opencode configuration, setup, or maintenance.

**Key principle**: Start minimal, validate often, layer complexity progressively.
