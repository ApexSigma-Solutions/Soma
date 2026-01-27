#!/usr/bin/env pwsh
# Quick fix for "Extension context invalidated" errors
# After reloading the extension, this reminds you to reload tabs

Write-Host "`n" -ForegroundColor Red
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Red
Write-Host "⚠️  EXTENSION CONTEXT INVALIDATED - SIMPLE FIX" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Red
Write-Host ""
Write-Host "🔴 Problem:" -ForegroundColor Red
Write-Host "   You reloaded the extension while chat tabs were open" -ForegroundColor Gray
Write-Host "   This broke the connection between extension and tabs" -ForegroundColor Gray
Write-Host ""
Write-Host "✅ Solution (30 seconds):" -ForegroundColor Green
Write-Host "   1. Go to ChatGPT tab → Press F5" -ForegroundColor White
Write-Host "   2. Go to Gemini tab → Press F5" -ForegroundColor White
Write-Host "   3. Go to Claude tab → Press F5" -ForegroundColor White
Write-Host "   4. Check console: [Omega_KG] Started capturing: [platform]" -ForegroundColor White
Write-Host "   5. Send a test message" -ForegroundColor White
Write-Host ""
Write-Host "💡 Remember:" -ForegroundColor Cyan
Write-Host "   ALWAYS refresh AI chat tabs after reloading extension!" -ForegroundColor Yellow
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════`n" -ForegroundColor Red
