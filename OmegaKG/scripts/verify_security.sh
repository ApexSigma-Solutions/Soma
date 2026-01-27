#!/bin/bash
# Security Verification Script
# Checks for sensitive files and patterns in the repository

set -e

echo "==================================="
echo "Security Verification Script"
echo "==================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track if any issues found
ISSUES_FOUND=0

# Function to print results
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $2"
    else
        echo -e "${RED}✗ FAIL${NC}: $2"
        ISSUES_FOUND=1
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠ WARNING${NC}: $1"
}

echo "1. Checking for private key files..."
PRIVATE_KEYS=$(find . -type f \( \
    -name "*.pem" -o \
    -name "*.key" -o \
    -name "*.crt" -o \
    -name "*.p12" -o \
    -name "*.pfx" -o \
    -name "*.jks" -o \
    -name "*_rsa" -o \
    -name "*_dsa" -o \
    -name "*_ecdsa" -o \
    -name "*_ed25519" -o \
    -name "id_rsa*" -o \
    -name "*.priv" \
    \) -not -path "./.git/*" 2>/dev/null || true)

if [ -z "$PRIVATE_KEYS" ]; then
    print_result 0 "No private key files found"
else
    print_result 1 "Private key files found:"
    echo "$PRIVATE_KEYS"
fi
echo ""

echo "2. Checking for .env files (excluding examples)..."
ENV_FILES=$(find . -type f -name ".env" -not -path "./.git/*" 2>/dev/null || true)
if [ -z "$ENV_FILES" ]; then
    print_result 0 "No .env files found in repository"
else
    print_warning ".env files should not be committed:"
    echo "$ENV_FILES"
    echo ""
fi
echo ""

echo "3. Checking .gitignore for security patterns..."
REQUIRED_PATTERNS=("*.pem" "*.key" ".env")
MISSING_PATTERNS=""

for pattern in "${REQUIRED_PATTERNS[@]}"; do
    if ! grep -q "$pattern" .gitignore 2>/dev/null; then
        MISSING_PATTERNS="$MISSING_PATTERNS $pattern"
    fi
done

if [ -z "$MISSING_PATTERNS" ]; then
    print_result 0 "Required .gitignore patterns present"
else
    print_result 1 "Missing .gitignore patterns:$MISSING_PATTERNS"
fi
echo ""

echo "4. Checking git history for sensitive files..."
HISTORY_CHECK=$(git log --all --full-history --oneline -- "*.pem" "*.key" 2>/dev/null | head -5 || true)
if [ -z "$HISTORY_CHECK" ]; then
    print_result 0 "No sensitive files found in git history"
else
    print_result 1 "Sensitive files found in git history:"
    echo "$HISTORY_CHECK"
    echo ""
    echo "Run: git log --all --full-history -- *.pem"
fi
echo ""

echo "5. Checking for hardcoded API keys..."
# Check for common API key patterns
API_KEY_PATTERNS=(
    "sk-[a-zA-Z0-9]{20,}"  # OpenAI style
    "AIza[a-zA-Z0-9_-]{35}" # Google API
    "AKIA[a-zA-Z0-9]{16}"   # AWS Access Key
    "ghp_[a-zA-Z0-9]{36}"   # GitHub Personal Access Token
)

FOUND_KEYS=""
for pattern in "${API_KEY_PATTERNS[@]}"; do
    MATCHES=$(grep -r -E "$pattern" --include="*.py" --include="*.js" --include="*.ts" . 2>/dev/null | grep -v ".git" | grep -v "node_modules" | head -2 || true)
    if [ ! -z "$MATCHES" ]; then
        FOUND_KEYS="$FOUND_KEYS\n$MATCHES"
    fi
done

if [ -z "$FOUND_KEYS" ]; then
    print_result 0 "No hardcoded API keys detected"
else
    print_result 1 "Potential hardcoded API keys found:"
    echo -e "$FOUND_KEYS"
fi
echo ""

echo "6. Checking pre-commit hooks..."
if [ -f ".pre-commit-config.yaml" ]; then
    if grep -q "detect-private-key" .pre-commit-config.yaml; then
        print_result 0 "Pre-commit detect-private-key hook configured"
    else
        print_result 1 "Pre-commit detect-private-key hook not configured"
    fi
else
    print_result 1 "No .pre-commit-config.yaml found"
fi
echo ""

echo "7. Checking security documentation..."
SECURITY_DOCS=("SECURITY.md" "docs/SECURITY_INCIDENT_PEM.md" "docs/SECURITY_RUNBOOK.md")
MISSING_DOCS=""

for doc in "${SECURITY_DOCS[@]}"; do
    if [ ! -f "$doc" ]; then
        MISSING_DOCS="$MISSING_DOCS $doc"
    fi
done

if [ -z "$MISSING_DOCS" ]; then
    print_result 0 "All security documentation present"
else
    print_result 1 "Missing security documentation:$MISSING_DOCS"
fi
echo ""

echo "8. Checking for large files (>1MB)..."
LARGE_FILES=$(find . -type f -size +1M -not -path "./.git/*" -not -path "./node_modules/*" -not -path "./.venv/*" -not -path "./venv/*" 2>/dev/null || true)
if [ -z "$LARGE_FILES" ]; then
    print_result 0 "No unusually large files found"
else
    print_warning "Large files found (review if they should be in git):"
    echo "$LARGE_FILES" | while read line; do
        SIZE=$(du -h "$line" | cut -f1)
        echo "  $SIZE - $line"
    done
fi
echo ""

echo "==================================="
echo "Security Verification Complete"
echo "==================================="
echo ""

if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}All security checks passed!${NC}"
    exit 0
else
    echo -e "${RED}Security issues found. Please review and fix.${NC}"
    echo ""
    echo "See SECURITY.md for security best practices."
    echo "See docs/SECURITY_RUNBOOK.md for remediation steps."
    exit 1
fi
