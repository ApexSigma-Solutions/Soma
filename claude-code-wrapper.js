#!/usr/bin/env node
/**
 * Claude Code Wrapper for VS Code Extension
 * This script properly spawns the npm-installed Claude Code CLI
 * and handles the .cmd wrapper execution through cmd.exe
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Path to the actual claude.cmd wrapper
const CLAUDE_CMD_PATH = path.join(
  process.env.APPDATA || path.join(process.env.USERPROFILE, 'AppData', 'Roaming'),
  'npm',
  'claude.cmd'
);

// Get all command line arguments (skip the wrapper script path)
const args = process.argv.slice(2);

// Verify the claude.cmd exists
if (!fs.existsSync(CLAUDE_CMD_PATH)) {
  console.error(`Error: Claude Code not found at ${CLAUDE_CMD_PATH}`);
  console.error('Please ensure @anthropic-ai/claude-code is installed globally via npm');
  process.exit(1);
}

// Spawn claude.cmd through cmd.exe on Windows
const windowsShell = process.platform === 'win32';

if (windowsShell) {
  // On Windows, we need to use cmd.exe to execute .cmd files
  const child = spawn('cmd.exe', ['/c', CLAUDE_CMD_PATH, ...args], {
    stdio: 'inherit',
    cwd: process.cwd(),
    env: process.env,
    windowsHide: false
  });

  child.on('error', (err) => {
    console.error('Failed to spawn Claude Code:', err.message);
    process.exit(1);
  });

  child.on('exit', (code) => {
    process.exit(code);
  });
} else {
  // On Unix-like systems, execute directly
  const child = spawn(CLAUDE_CMD_PATH, args, {
    stdio: 'inherit',
    cwd: process.cwd(),
    env: process.env
  });

  child.on('error', (err) => {
    console.error('Failed to spawn Claude Code:', err.message);
    process.exit(1);
  });

  child.on('exit', (code) => {
    process.exit(code);
  });
}
