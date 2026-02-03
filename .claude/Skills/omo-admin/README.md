# Oh-My-OpenCode Administrator Skill

Complete administration toolkit for the [oh-my-opencode](https://github.com/code-yeongyu/oh-my-opencode) plugin.

## Quick Start

This skill helps you:
- ✅ Install oh-my-opencode from scratch
- ✅ Configure agents, categories, and models
- ✅ Optimize for your available providers
- ✅ Troubleshoot common issues
- ✅ Maintain and update the plugin

## Usage

Just ask the agent to help with oh-my-opencode:

```
"Install and configure oh-my-opencode for me"
"Set up Sisyphus with optimal settings"
"My oracle agent keeps using the wrong model, fix it"
"Diagnose my omo configuration"
"Enable tmux integration"
```

The agent will use this skill automatically when you mention oh-my-opencode or omo.

## What's Included

### Core Documentation
- **SKILL.md**: Complete administration guide with workflows, patterns, and best practices

### Templates
Ready-to-use configuration templates:
- `templates/minimal.jsonc`: Bare minimum (uses all defaults)
- `templates/essential.jsonc`: Recommended starting point (optimizes categories)
- `templates/power-user.jsonc`: Full agent/category optimization
- `templates/advanced.jsonc`: All features enabled (tmux, custom LSP, etc.)

### Utilities
- `utilities/config-validator.js`: Validate oh-my-opencode.jsonc files
  ```bash
  node utilities/config-validator.js ~/.config/opencode/oh-my-opencode.jsonc
  ```

### Checklists
- `checklists/installation.md`: Step-by-step installation checklist
- `checklists/troubleshooting.md`: Quick diagnostic guide for common issues

## Common Tasks

### First-Time Installation
```
Agent: "Follow the installation guide at checklists/installation.md"
```

The agent will:
1. Check prerequisites (OpenCode version, providers)
2. Add plugin to OpenCode config
3. Run interactive installer
4. Verify with `doctor` command
5. Configure categories for available providers

### Optimize Configuration
```
Agent: "Check available models, then apply essential template"
```

The agent will:
1. Run `opencode models` to see what's available
2. Choose appropriate template (essential, power-user, etc.)
3. Customize based on your providers
4. Validate with config-validator
5. Test with `doctor` command

### Troubleshoot Issues
```
Agent: "Use troubleshooting guide to diagnose the issue"
```

The agent will:
1. Run diagnostic commands (`doctor`, `opencode models`)
2. Identify the problem from checklists/troubleshooting.md
3. Apply the recommended solution
4. Verify the fix

## File Structure

```
omo-admin/
├── SKILL.md                          # Main skill documentation
├── README.md                         # This file
├── templates/                        # Configuration templates
│   ├── minimal.jsonc
│   ├── essential.jsonc
│   ├── power-user.jsonc
│   └── advanced.jsonc
├── utilities/                        # Helper scripts
│   └── config-validator.js           # JSONC validator
└── checklists/                       # Step-by-step guides
    ├── installation.md
    └── troubleshooting.md
```

## Configuration Locations

| File | Purpose |
|------|---------|
| `~/.config/opencode/opencode.json` | OpenCode main config (add plugin here) |
| `~/.config/opencode/oh-my-opencode.jsonc` | User-level omo config |
| `.opencode/oh-my-opencode.jsonc` | Project-level omo config (higher priority) |

## Quick Reference

### Essential Commands
```bash
# Install plugin
bunx oh-my-opencode install

# Check health
bunx oh-my-opencode doctor --verbose

# List available models
opencode models

# Validate config
node .claude/skills/omo-admin/utilities/config-validator.js ~/.config/opencode/oh-my-opencode.jsonc
```

### Config Template Selection

| Template | Use When |
|----------|----------|
| **minimal** | Testing, first-time setup |
| **essential** | Most users (recommended) |
| **power-user** | Full agent/category optimization |
| **advanced** | Need tmux, custom LSP, experimental features |

### Agent Workflow Examples

**Example 1**: First-time setup
```
User: "Install oh-my-opencode"
Agent: 
  1. Reads checklists/installation.md
  2. Checks opencode --version
  3. Checks opencode models
  4. Adds plugin to opencode.json
  5. Runs bunx oh-my-opencode install
  6. Verifies with doctor
```

**Example 2**: Optimize for providers
```
User: "I have Anthropic and Google, optimize my config"
Agent:
  1. Runs opencode models
  2. Identifies available models
  3. Applies templates/power-user.jsonc
  4. Customizes for Anthropic + Google
  5. Validates with config-validator
  6. Tests with doctor
```

**Example 3**: Troubleshoot
```
User: "Oracle keeps using Sonnet instead of GPT"
Agent:
  1. Reads checklists/troubleshooting.md
  2. Checks "Model Not Available" section
  3. Runs diagnostic commands
  4. Applies fix (add model override)
  5. Verifies resolution
```

## Best Practices

1. **Start Minimal**: Use templates/minimal.jsonc first, add features incrementally
2. **Validate Often**: Run `doctor` after every config change
3. **Use JSONC**: Always use `.jsonc` extension (allows comments, trailing commas)
4. **Document Custom**: Explain why you made custom configurations
5. **Monitor Costs**: Configure `quick` category to use Haiku for cost savings

## Troubleshooting

Common issues and fixes:

| Issue | Quick Fix |
|-------|-----------|
| Plugin not loading | Add `"oh-my-opencode"` to `opencode.json` plugin array |
| Categories use wrong model | Add categories to config (they don't use defaults automatically) |
| Background tasks sequential | Set `background_task.defaultConcurrency` > 1 |
| Tmux not working | Must run inside tmux with `opencode --port 4096` |
| JSON parsing errors | Use `.jsonc` extension, check for missing commas |

Full troubleshooting guide: `checklists/troubleshooting.md`

## External Resources

- **Plugin Repository**: https://github.com/code-yeongyu/oh-my-opencode
- **Configuration Docs**: https://github.com/code-yeongyu/oh-my-opencode/blob/dev/docs/configurations.md
- **Feature Docs**: https://github.com/code-yeongyu/oh-my-opencode/blob/dev/docs/features.md
- **Discord Community**: https://discord.gg/PUwSMR9XNk

## Schema

Configuration autocomplete available via:
```jsonc
{
  "$schema": "https://raw.githubusercontent.com/code-yeongyu/oh-my-opencode/master/assets/oh-my-opencode.schema.json"
}
```

## Updates

Keep the plugin updated:
```bash
bun update oh-my-opencode
```

Check for skill updates by reviewing the oh-my-opencode repository.

---

**Need Help?** The agent will automatically use this skill when you mention oh-my-opencode administration tasks. Just ask naturally!
