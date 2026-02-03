# Oh-My-OpenCode Installation Checklist

Use this checklist to ensure complete installation and setup.

## Pre-Installation

- [ ] **Check OpenCode version**
  ```bash
  opencode --version
  ```
  - Recommended: 1.0.133 or newer
  - Minimum: 1.0.132
  
- [ ] **Check available providers**
  ```bash
  opencode models
  ```
  - Note which providers you have: Anthropic, OpenAI, Google, etc.
  
- [ ] **Check Node.js/Bun installed**
  ```bash
  node --version
  # or
  bun --version
  ```

## Installation Steps

- [ ] **Add plugin to OpenCode config**
  - Edit: `~/.config/opencode/opencode.json` (or `.jsonc`)
  - Add `"oh-my-opencode"` to `plugin` array
  - Example:
    ```jsonc
    {
      "plugin": [
        "oh-my-opencode"
      ]
    }
    ```

- [ ] **Run interactive installer** (Recommended)
  ```bash
  bunx oh-my-opencode install
  ```
  - Answer questions about available providers
  - Let it generate optimal configuration

- [ ] **OR manually create config** (Alternative)
  - Create: `~/.config/opencode/oh-my-opencode.jsonc`
  - Start with minimal template
  - Add schema for autocomplete

## Verification

- [ ] **Run doctor command**
  ```bash
  bunx oh-my-opencode doctor --verbose
  ```
  - Check: ✅ Plugin loaded successfully
  - Check: ✅ Configuration file valid
  - Check: ✅ Model resolution working
  - Check: ✅ All required providers available

- [ ] **Test in OpenCode**
  ```bash
  opencode
  ```
  - Verify Sisyphus agent available
  - Test basic functionality
  - Check for any error messages

## Configuration Optimization

- [ ] **Configure categories** (Recommended)
  - Add at least `quick` category for cost savings
  - Configure `visual-engineering` if you have Gemini
  - Configure `ultrabrain` if you have GPT-5.2
  
  Example:
  ```jsonc
  {
    "categories": {
      "quick": { "model": "anthropic/claude-haiku-4-5" },
      "visual-engineering": { "model": "google/gemini-3-pro-preview" }
    }
  }
  ```

- [ ] **Set background task limits** (Optional)
  ```jsonc
  {
    "background_task": {
      "defaultConcurrency": 5,
      "providerConcurrency": {
        "anthropic": 3
      }
    }
  }
  ```

- [ ] **Configure git-master** (Optional)
  ```jsonc
  {
    "git_master": {
      "commit_footer": true,
      "include_co_authored_by": true
    }
  }
  ```

## Advanced Setup (Optional)

- [ ] **Tmux integration**
  - Only if you want to see background agents in separate panes
  - Requires running inside tmux
  - Must use `opencode --port 4096`
  
  ```jsonc
  {
    "tmux": {
      "enabled": true,
      "layout": "main-vertical"
    }
  }
  ```

- [ ] **Agent permissions**
  - Fine-tune what specific agents can do
  
  ```jsonc
  {
    "agents": {
      "explore": {
        "permission": {
          "edit": "deny",
          "bash": { "git": "allow" }
        }
      }
    }
  }
  ```

- [ ] **Custom LSP servers**
  ```jsonc
  {
    "lsp": {
      "typescript-language-server": {
        "command": ["typescript-language-server", "--stdio"],
        "extensions": [".ts", ".tsx"]
      }
    }
  }
  ```

## Post-Installation

- [ ] **Document configuration**
  - Add README to `.opencode/` explaining team setup
  - Note any custom configurations
  - Document provider requirements

- [ ] **Test key workflows**
  - [ ] Basic task delegation: `delegate_task(category="quick", ...)`
  - [ ] Background agents: `delegate_task(run_in_background=true, ...)`
  - [ ] Agent-specific tasks: `delegate_task(agent="oracle", ...)`

- [ ] **Monitor costs**
  - Watch for excessive Opus usage
  - Verify Haiku used for trivial tasks
  - Check background task concurrency

## Common Post-Install Tasks

- [ ] **Bookmark doctor command**
  ```bash
  alias omo-doctor='bunx oh-my-opencode doctor --verbose'
  ```

- [ ] **Create shell function for tmux** (if using)
  ```fish
  # ~/.config/fish/config.fish
  function oc
      opencode --port 4096 $argv
  end
  ```

- [ ] **Set up update checks**
  ```bash
  # Periodically check for updates
  bun update oh-my-opencode
  ```

## Troubleshooting

If anything fails:

1. **Check logs**: OpenCode error output
2. **Run doctor**: `bunx oh-my-opencode doctor --verbose`
3. **Validate config**: Use config-validator utility
4. **Check providers**: `opencode models`
5. **Check OpenCode version**: `opencode --version`

## Success Criteria

Installation is complete when:

- ✅ `bunx oh-my-opencode doctor` shows all green
- ✅ Sisyphus agent appears in OpenCode
- ✅ Categories use optimal models (not all using system default)
- ✅ Background tasks can run in parallel
- ✅ No error messages in OpenCode startup

---

**Need help?** Check SKILL.md for detailed documentation or run:
```bash
bunx oh-my-opencode doctor --verbose
```
