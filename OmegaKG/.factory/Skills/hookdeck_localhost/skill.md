---
name: hookdeck-localhost-debugging
description: Test and debug webhook integrations on localhost using Hookdeck CLI. Use when developing webhook handlers, testing webhook delivery locally, debugging webhook failures, or setting up team webhook development workflows.
allowed-tools: Write, Read, Bash
---

# Hookdeck Localhost Debugging

## Quick Start

Receive webhooks on your local development server in 3 steps:

```bash
# 1. Start your local server (if not running)
npm start  # or your dev command

# 2. Start Hookdeck CLI to forward webhooks to your localhost
hookdeck listen 3000 stripe-source

# 3. Copy the displayed Source URL and register it with your webhook provider
# Webhooks will now flow directly to your local server!
```
