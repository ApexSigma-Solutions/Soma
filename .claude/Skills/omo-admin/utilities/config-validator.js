#!/usr/bin/env node
/**
 * Oh-My-OpenCode Configuration Validator
 * 
 * Validates oh-my-opencode.jsonc files against the schema and checks
 * for common configuration errors.
 * 
 * Usage:
 *   node config-validator.js <config-file-path>
 *   node config-validator.js ~/.config/opencode/oh-my-opencode.jsonc
 */

const fs = require('fs');
const path = require('path');

// JSONC parser (simple implementation - strips comments and allows trailing commas)
function parseJSONC(content) {
  // Remove line comments
  content = content.replace(/\/\/.*$/gm, '');
  // Remove block comments
  content = content.replace(/\/\*[\s\S]*?\*\//g, '');
  // Remove trailing commas
  content = content.replace(/,(\s*[}\]])/g, '$1');
  
  return JSON.parse(content);
}

// Validation rules
const validationRules = {
  // Check if $schema is present
  checkSchema(config) {
    if (!config.$schema) {
      return {
        level: 'warning',
        message: 'Missing $schema property. Add for autocomplete support:\n  "$schema": "https://raw.githubusercontent.com/code-yeongyu/oh-my-opencode/master/assets/oh-my-opencode.schema.json"'
      };
    }
    return null;
  },

  // Check for valid agent names
  checkAgentNames(config) {
    if (!config.agents) return null;
    
    const validAgents = [
      'Sisyphus', 'oracle', 'librarian', 'explore', 'multimodal-looker',
      'OpenCode-Builder', 'Prometheus (Planner)', 'Metis (Plan Consultant)',
      'Momus (Plan Reviewer)', 'Atlas', 'build', 'plan'
    ];
    
    const errors = [];
    for (const agent of Object.keys(config.agents)) {
      if (!validAgents.includes(agent)) {
        errors.push({
          level: 'warning',
          message: `Unknown agent "${agent}". Valid agents: ${validAgents.join(', ')}`
        });
      }
    }
    
    return errors.length > 0 ? errors : null;
  },

  // Check for valid category names
  checkCategoryNames(config) {
    if (!config.categories) return null;
    
    const validCategories = [
      'visual-engineering', 'ultrabrain', 'artistry', 'quick',
      'unspecified-low', 'unspecified-high', 'writing'
    ];
    
    const warnings = [];
    for (const category of Object.keys(config.categories)) {
      if (!validCategories.includes(category)) {
        warnings.push({
          level: 'info',
          message: `Custom category "${category}". Built-in categories: ${validCategories.join(', ')}`
        });
      }
    }
    
    return warnings.length > 0 ? warnings : null;
  },

  // Check for valid hook names
  checkDisabledHooks(config) {
    if (!config.disabled_hooks) return null;
    
    const validHooks = [
      'todo-continuation-enforcer', 'context-window-monitor', 'session-recovery',
      'session-notification', 'comment-checker', 'grep-output-truncator',
      'tool-output-truncator', 'directory-agents-injector', 'directory-readme-injector',
      'empty-task-response-detector', 'think-mode', 'anthropic-context-window-limit-recovery',
      'rules-injector', 'background-notification', 'auto-update-checker',
      'startup-toast', 'keyword-detector', 'agent-usage-reminder',
      'non-interactive-env', 'interactive-bash-session', 'compaction-context-injector',
      'thinking-block-validator', 'claude-code-hooks', 'ralph-loop', 'preemptive-compaction'
    ];
    
    const errors = [];
    for (const hook of config.disabled_hooks) {
      if (!validHooks.includes(hook)) {
        errors.push({
          level: 'warning',
          message: `Unknown hook "${hook}". Valid hooks: ${validHooks.join(', ')}`
        });
      }
    }
    
    return errors.length > 0 ? errors : null;
  },

  // Check model format
  checkModelFormat(config) {
    const errors = [];
    
    function checkModel(model, context) {
      if (!model) return;
      
      // Model should be in format: provider/model-name
      if (!model.includes('/')) {
        errors.push({
          level: 'error',
          message: `Invalid model format in ${context}: "${model}". Expected format: "provider/model-name" (e.g., "anthropic/claude-opus-4-5")`
        });
      }
    }
    
    // Check agents
    if (config.agents) {
      for (const [agent, settings] of Object.entries(config.agents)) {
        if (settings.model) {
          checkModel(settings.model, `agents.${agent}.model`);
        }
      }
    }
    
    // Check categories
    if (config.categories) {
      for (const [category, settings] of Object.entries(config.categories)) {
        if (settings.model) {
          checkModel(settings.model, `categories.${category}.model`);
        }
      }
    }
    
    return errors.length > 0 ? errors : null;
  },

  // Check background task concurrency
  checkBackgroundTaskConcurrency(config) {
    if (!config.background_task) return null;
    
    const warnings = [];
    const bt = config.background_task;
    
    if (bt.defaultConcurrency && bt.defaultConcurrency < 1) {
      warnings.push({
        level: 'error',
        message: 'background_task.defaultConcurrency must be >= 1'
      });
    }
    
    if (bt.providerConcurrency) {
      for (const [provider, limit] of Object.entries(bt.providerConcurrency)) {
        if (limit < 1) {
          warnings.push({
            level: 'error',
            message: `background_task.providerConcurrency.${provider} must be >= 1`
          });
        }
      }
    }
    
    if (bt.modelConcurrency) {
      for (const [model, limit] of Object.entries(bt.modelConcurrency)) {
        if (limit < 1) {
          warnings.push({
            level: 'error',
            message: `background_task.modelConcurrency["${model}"] must be >= 1`
          });
        }
      }
    }
    
    return warnings.length > 0 ? warnings : null;
  },

  // Check tmux configuration
  checkTmuxConfig(config) {
    if (!config.tmux || !config.tmux.enabled) return null;
    
    const warnings = [];
    const tmux = config.tmux;
    
    const validLayouts = [
      'main-vertical', 'main-horizontal', 'tiled',
      'even-horizontal', 'even-vertical'
    ];
    
    if (tmux.layout && !validLayouts.includes(tmux.layout)) {
      warnings.push({
        level: 'error',
        message: `Invalid tmux layout "${tmux.layout}". Valid options: ${validLayouts.join(', ')}`
      });
    }
    
    if (tmux.main_pane_size && (tmux.main_pane_size < 20 || tmux.main_pane_size > 80)) {
      warnings.push({
        level: 'warning',
        message: 'tmux.main_pane_size should be between 20-80 (percentage)'
      });
    }
    
    return warnings.length > 0 ? warnings : null;
  },

  // Warn about experimental features
  checkExperimental(config) {
    if (!config.experimental) return null;
    
    const warnings = [];
    const exp = config.experimental;
    
    if (exp.truncate_all_tool_outputs) {
      warnings.push({
        level: 'warning',
        message: 'experimental.truncate_all_tool_outputs enabled - may truncate important output'
      });
    }
    
    if (exp.aggressive_truncation) {
      warnings.push({
        level: 'warning',
        message: 'experimental.aggressive_truncation enabled - may cause unexpected behavior'
      });
    }
    
    if (exp.auto_resume) {
      warnings.push({
        level: 'warning',
        message: 'experimental.auto_resume enabled - experimental feature, use with caution'
      });
    }
    
    return warnings.length > 0 ? warnings : null;
  }
};

// Main validation function
function validateConfig(configPath) {
  console.log(`\n🔍 Validating: ${configPath}\n`);
  
  // Check file exists
  if (!fs.existsSync(configPath)) {
    console.error(`❌ File not found: ${configPath}`);
    process.exit(1);
  }
  
  // Read and parse file
  let config;
  try {
    const content = fs.readFileSync(configPath, 'utf8');
    config = parseJSONC(content);
    console.log('✅ JSONC syntax valid\n');
  } catch (error) {
    console.error(`❌ JSON parsing error: ${error.message}`);
    process.exit(1);
  }
  
  // Run validation rules
  const results = {
    errors: [],
    warnings: [],
    info: []
  };
  
  for (const [ruleName, ruleFunc] of Object.entries(validationRules)) {
    const result = ruleFunc(config);
    if (result) {
      const items = Array.isArray(result) ? result : [result];
      items.forEach(item => {
        results[item.level === 'error' ? 'errors' : item.level === 'warning' ? 'warnings' : 'info'].push({
          rule: ruleName,
          message: item.message
        });
      });
    }
  }
  
  // Print results
  if (results.errors.length > 0) {
    console.log('🔴 ERRORS:\n');
    results.errors.forEach(err => {
      console.log(`  ❌ ${err.message}`);
      console.log(`     (${err.rule})\n`);
    });
  }
  
  if (results.warnings.length > 0) {
    console.log('🟡 WARNINGS:\n');
    results.warnings.forEach(warn => {
      console.log(`  ⚠️  ${warn.message}`);
      console.log(`     (${warn.rule})\n`);
    });
  }
  
  if (results.info.length > 0) {
    console.log('ℹ️  INFO:\n');
    results.info.forEach(info => {
      console.log(`  ℹ️  ${info.message}`);
      console.log(`     (${info.rule})\n`);
    });
  }
  
  // Summary
  console.log('─'.repeat(60));
  if (results.errors.length === 0 && results.warnings.length === 0) {
    console.log('✅ Configuration valid!');
  } else {
    console.log(`Summary: ${results.errors.length} errors, ${results.warnings.length} warnings, ${results.info.length} info`);
  }
  
  process.exit(results.errors.length > 0 ? 1 : 0);
}

// CLI
if (require.main === module) {
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    console.error('Usage: node config-validator.js <config-file-path>');
    console.error('Example: node config-validator.js ~/.config/opencode/oh-my-opencode.jsonc');
    process.exit(1);
  }
  
  const configPath = args[0].replace(/^~/, process.env.HOME || process.env.USERPROFILE);
  validateConfig(configPath);
}

module.exports = { validateConfig, parseJSONC };
