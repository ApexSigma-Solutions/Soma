# Oh-My-OpenCode Troubleshooting Guide

Quick diagnostic guide for common issues.

## 🔍 First Steps

**Always start here:**

```bash
# 1. Check plugin loaded
bunx oh-my-opencode doctor --verbose

# 2. Check available models
opencode models

# 3. Check OpenCode version
opencode --version

# 4. Validate config
node .claude/skills/omo-admin/utilities/config-validator.js ~/.config/opencode/oh-my-opencode.jsonc
```

## Common Issues

### ❌ Plugin Not Loading

**Symptoms**: oh-my-opencode features don't work, no Sisyphus agent

**Diagnostic**:
```bash
# Check OpenCode config
cat ~/.config/opencode/opencode.json | grep "oh-my-opencode"
```

**Solutions**:
1. Add plugin to OpenCode config:
   ```jsonc
   {
     "plugin": [
       "oh-my-opencode"
     ]
   }
   ```

2. Verify installation:
   ```bash
   bunx oh-my-opencode --version
   ```

3. Reinstall if needed:
   ```bash
   bunx oh-my-opencode install
   ```

---

### ❌ Model Not Available

**Symptoms**: "Model not found" errors, agent falls back to default

**Diagnostic**:
```bash
# Check what models are available
opencode models

# Check model resolution
bunx oh-my-opencode doctor --verbose
# Look for the "Model Resolution" section
```

**Solutions**:
1. **Model doesn't exist**: Update config to use available model
   ```jsonc
   {
     "agents": {
       "oracle": {
         "model": "anthropic/claude-sonnet-4-5"  // Use available model
       }
     }
   }
   ```

2. **Provider not configured**: Add provider in OpenCode
   ```bash
   # Example: Add OpenAI provider
   # Edit ~/.config/opencode/opencode.json
   {
     "providers": {
       "openai": {
         "apiKey": "sk-..."
       }
     }
   }
   ```

3. **Wrong model name**: Check spelling
   ```bash
   opencode models | grep -i "claude"  # Search for correct name
   ```

---

### ❌ Categories Using System Default Model

**Symptoms**: All tasks use same model, expensive model used for trivial tasks

**Diagnostic**:
```bash
bunx oh-my-opencode doctor --verbose
# Check "Model Resolution" → Categories section
```

**Root Cause**: Categories not configured in oh-my-opencode.json

**Solution**: Add categories to config
```jsonc
{
  "categories": {
    "quick": { "model": "anthropic/claude-haiku-4-5" },
    "visual-engineering": { "model": "google/gemini-3-pro-preview" }
  }
}
```

**Why this happens**: Model resolution priority is:
1. User override (in config) ← **Need this**
2. Category built-in default
3. System default (from opencode.json) ← **Currently falling back here**

---

### ❌ Background Tasks Not Running

**Symptoms**: `delegate_task(run_in_background=true)` doesn't spawn parallel tasks

**Diagnostic**:
```bash
# Check concurrency config
cat ~/.config/opencode/oh-my-opencode.jsonc | grep -A 10 "background_task"
```

**Solutions**:
1. **No concurrency configured**: Add limits
   ```jsonc
   {
     "background_task": {
       "defaultConcurrency": 5
     }
   }
   ```

2. **Limits too low**: Increase
   ```jsonc
   {
     "background_task": {
       "defaultConcurrency": 5,
       "providerConcurrency": {
         "anthropic": 3,  // Increase if needed
         "google": 10
       }
     }
   }
   ```

3. **Provider rate limits**: Check provider dashboard for API limits

---

### ❌ Tmux Integration Not Working

**Symptoms**: Background agents don't appear in tmux panes

**Diagnostic**:
```bash
# 1. Check if inside tmux
echo $TMUX
# Should output: /tmp/tmux-... (if inside tmux)

# 2. Check OpenCode running with port
ps aux | grep "opencode.*--port"
# Should show: opencode --port 4096

# 3. Check config
cat ~/.config/opencode/oh-my-opencode.jsonc | grep -A 5 "tmux"
```

**Solutions**:

**Problem**: Not inside tmux
```bash
# Start tmux session first
tmux new -s dev
# Then run opencode
opencode --port 4096
```

**Problem**: OpenCode not running with `--port`
```bash
# Must use --port flag
opencode --port 4096
```

**Problem**: Tmux not enabled in config
```jsonc
{
  "tmux": {
    "enabled": true,  // Must be true
    "layout": "main-vertical"
  }
}
```

**Recommended**: Create shell function
```fish
# ~/.config/fish/config.fish
function oc
    # Auto-find available port
    set port 4096
    while lsof -i :$port >/dev/null 2>&1
        set port (math $port + 1)
    end
    
    if set -q TMUX
        opencode --port $port $argv
    else
        tmux new-session "opencode --port $port $argv"
    end
end
```

---

### ❌ JSON Parsing Errors

**Symptoms**: "Invalid JSON", "Unexpected token", config not loading

**Diagnostic**:
```bash
# Validate JSON syntax
jq . ~/.config/opencode/oh-my-opencode.jsonc

# Or use config validator
node .claude/skills/omo-admin/utilities/config-validator.js ~/.config/opencode/oh-my-opencode.jsonc
```

**Common Causes**:

1. **Missing comma**:
   ```jsonc
   // ❌ Wrong
   {
     "agents": {
       "oracle": { "model": "openai/gpt-5.2" }
       "librarian": { "model": "anthropic/claude-sonnet-4-5" }
     }
   }
   
   // ✅ Correct
   {
     "agents": {
       "oracle": { "model": "openai/gpt-5.2" },  // Add comma
       "librarian": { "model": "anthropic/claude-sonnet-4-5" }
     }
   }
   ```

2. **Trailing comma after last property** (OK in JSONC, error in strict JSON):
   ```jsonc
   // ✅ OK in JSONC
   {
     "agents": {
       "oracle": { "model": "openai/gpt-5.2" },  // Trailing comma OK
     },  // This is also OK
   }
   ```

3. **Unclosed brackets**:
   ```jsonc
   // ❌ Wrong
   {
     "agents": {
       "oracle": { "model": "openai/gpt-5.2" }
     // Missing }
   }
   
   // ✅ Correct
   {
     "agents": {
       "oracle": { "model": "openai/gpt-5.2" }
     }
   }
   ```

4. **Comments in wrong places**:
   ```jsonc
   // ❌ Wrong - comment inside string
   {
     "model": "anthropic/claude-opus-4-5 // My favorite model"
   }
   
   // ✅ Correct
   {
     "model": "anthropic/claude-opus-4-5"  // My favorite model
   }
   ```

**Solution**: Use `.jsonc` extension and JSONC-aware tools

---

### ❌ Agent Not Responding

**Symptoms**: Delegate task hangs, no response from specific agent

**Diagnostic**:
```bash
# 1. Check agent not disabled
cat ~/.config/opencode/oh-my-opencode.jsonc | grep "disabled_agents"

# 2. Check agent model available
bunx oh-my-opencode doctor --verbose

# 3. Check OpenCode logs for errors
```

**Solutions**:

1. **Agent disabled**: Remove from disabled list
   ```jsonc
   {
     "disabled_agents": [
       // "oracle"  // Remove this line
     ]
   }
   ```

2. **Model unavailable**: Update agent model
   ```jsonc
   {
     "agents": {
       "oracle": {
         "model": "anthropic/claude-sonnet-4-5"  // Use available model
       }
     }
   }
   ```

3. **Permission issues**: Check permissions
   ```jsonc
   {
     "agents": {
       "oracle": {
         "permission": {
           "bash": "allow",  // May need to grant permissions
           "edit": "allow"
         }
       }
     }
   }
   ```

---

### ❌ High Costs / Rate Limits

**Symptoms**: Unexpected API costs, rate limit errors

**Diagnostic**:
```bash
# Check which models are being used
bunx oh-my-opencode doctor --verbose
# Review "Model Resolution" section
```

**Solutions**:

1. **Configure `quick` category** (most important):
   ```jsonc
   {
     "categories": {
       "quick": { 
         "model": "anthropic/claude-haiku-4-5"  // Cheap for trivial tasks
       }
     }
   }
   ```

2. **Limit expensive model concurrency**:
   ```jsonc
   {
     "background_task": {
       "modelConcurrency": {
         "anthropic/claude-opus-4-5": 2,  // Max 2 concurrent Opus
         "openai/gpt-5.2": 3
       }
     }
   }
   ```

3. **Use free models where possible**:
   ```jsonc
   {
     "agents": {
       "explore": { 
         "model": "opencode/gpt-5-nano"  // Free for exploration
       }
     }
   }
   ```

4. **Review background task limits**:
   ```jsonc
   {
     "background_task": {
       "defaultConcurrency": 3,  // Reduce to avoid rate limits
       "providerConcurrency": {
         "anthropic": 2  // Lower for strict limits
       }
     }
   }
   ```

---

### ❌ LSP Not Working

**Symptoms**: LSP features (rename, diagnostics) not available

**Diagnostic**:
```bash
# Check LSP server installed
which typescript-language-server
which pylsp

# Check LSP config
cat ~/.config/opencode/oh-my-opencode.jsonc | grep -A 10 "lsp"
```

**Solutions**:

1. **Install LSP server**:
   ```bash
   # TypeScript
   npm install -g typescript-language-server typescript
   
   # Python
   pip install python-lsp-server
   ```

2. **Add to config**:
   ```jsonc
   {
     "lsp": {
       "typescript-language-server": {
         "command": ["typescript-language-server", "--stdio"],
         "extensions": [".ts", ".tsx"]
       },
       "pylsp": {
         "command": ["pylsp"],
         "extensions": [".py"]
       }
     }
   }
   ```

3. **Check server in PATH**:
   ```bash
   which typescript-language-server
   # Should output: /usr/local/bin/typescript-language-server
   ```

---

## Quick Diagnostic Script

Save this as `diagnose-omo.sh`:

```bash
#!/bin/bash
echo "🔍 Oh-My-OpenCode Diagnostics"
echo "=============================="
echo ""

echo "1️⃣  OpenCode Version:"
opencode --version
echo ""

echo "2️⃣  Plugin Status:"
bunx oh-my-opencode doctor --verbose
echo ""

echo "3️⃣  Available Models:"
opencode models | head -20
echo "  ... (showing first 20)"
echo ""

echo "4️⃣  Config File:"
if [ -f ~/.config/opencode/oh-my-opencode.jsonc ]; then
    echo "  ✅ Found: ~/.config/opencode/oh-my-opencode.jsonc"
elif [ -f ~/.config/opencode/oh-my-opencode.json ]; then
    echo "  ✅ Found: ~/.config/opencode/oh-my-opencode.json"
else
    echo "  ❌ Not found"
fi
echo ""

echo "5️⃣  Tmux Status:"
if [ -n "$TMUX" ]; then
    echo "  ✅ Inside tmux session"
else
    echo "  ❌ Not in tmux"
fi
echo ""

echo "6️⃣  Background Port:"
if ps aux | grep -q "opencode.*--port"; then
    echo "  ✅ Running with --port"
    ps aux | grep "opencode.*--port" | grep -v grep
else
    echo "  ❌ Not running with --port"
fi
echo ""

echo "Done! Review output above for issues."
```

Usage:
```bash
chmod +x diagnose-omo.sh
./diagnose-omo.sh
```

---

## Still Having Issues?

1. **Check GitHub Issues**: [oh-my-opencode/issues](https://github.com/code-yeongyu/oh-my-opencode/issues)
2. **Join Discord**: [OpenCode Community](https://discord.gg/PUwSMR9XNk)
3. **Review Documentation**: Full docs in SKILL.md
4. **Run Doctor**: `bunx oh-my-opencode doctor --verbose`

## Prevention Checklist

Avoid common issues by:

- ✅ Always use `.jsonc` extension for config files
- ✅ Run `doctor` after every config change
- ✅ Use config-validator before applying changes
- ✅ Start with minimal config, add incrementally
- ✅ Document why you made custom configurations
- ✅ Keep oh-my-opencode updated: `bun update oh-my-opencode`
