#!/bin/bash

# OmegaKG Release Signing Script
# 
# This script provides GPG signing capabilities for releases
# Usage: ./scripts/sign-release.sh [version] [key-id]

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GPG_KEY_ID="${2:-}"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

usage() {
    cat << EOF
Usage: $0 [VERSION] [KEY_ID]

OmegaKG Release Signing Script

Arguments:
    VERSION    Version tag to sign (e.g., v1.0.0-core)
    KEY_ID     GPG key ID (optional, will use default if not provided)

Examples:
    $0 v1.0.0-core
    $0 v1.0.0-core ABC123DE
    
EOF
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if git is available
    if ! command -v git &> /dev/null; then
        log_error "Git is not installed or not in PATH"
        exit 1
    fi
    
    # Check if GPG is available
    if ! command -v gpg &> /dev/null; then
        log_error "GPG is not installed or not in PATH"
        exit 1
    fi
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir &> /dev/null; then
        log_error "Not in a git repository"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

validate_version() {
    local version="$1"
    
    if [[ -z "$version" ]]; then
        log_error "Version argument is required"
        usage
        exit 1
    fi
    
    # Check if tag exists
    if ! git show-ref --verify --quiet "refs/tags/$version"; then
        log_error "Tag '$version' does not exist"
        log_info "Available tags:"
        git tag --list | head -10
        exit 1
    fi
    
    log_success "Version '$version' validated"
}

get_gpg_key() {
    local key_id="$1"
    
    if [[ -n "$key_id" ]]; then
        # Verify the provided key exists
        if ! gpg --list-secret-keys "$key_id" &> /dev/null; then
            log_error "GPG key '$key_id' not found"
            log_info "Available secret keys:"
            gpg --list-secret-keys --keyid-format LONG | grep sec
            exit 1
        fi
        echo "$key_id"
    else
        # Try to get default signing key
        local default_key
        default_key=$(git config user.signingkey || gpg --list-secret-keys --keyid-format LONG | grep sec | head -1 | awk '{print $2}' | tail -1)
        
        if [[ -z "$default_key" ]]; then
            log_error "No GPG signing key found. Please provide a KEY_ID or configure git user.signingkey"
            log_info "Available secret keys:"
            gpg --list-secret-keys --keyid-format LONG | grep sec
            exit 1
        fi
        
        log_info "Using default GPG key: $default_key"
        echo "$default_key"
    fi
}

sign_tag() {
    local version="$1"
    local key_id="$2"
    
    log_info "Signing tag '$version' with GPG key '$key_id'..."
    
    # Set git config for this operation
    git config user.signingkey "$key_id"
    
    # Create signed tag (this will fail if the tag already exists, so we force it)
    if git tag -f -s "$version" -m "Release $version"; then
        log_success "Tag '$version' signed successfully"
    else
        log_error "Failed to sign tag '$version'"
        return 1
    fi
}

sign_release_artifacts() {
    local version="$1"
    
    log_info "Looking for release artifacts to sign..."
    
    # Find Python packages
    local pkg_dir="$REPO_ROOT/dist"
    if [[ -d "$pkg_dir" ]]; then
        log_info "Found Python packages in $pkg_dir"
        
        for file in "$pkg_dir"/*.whl "$pkg_dir"/*.tar.gz; do
            if [[ -f "$file" ]]; then
                log_info "Signing $(basename "$file")..."
                gpg --armor --detach-sign "$file"
                log_success "Signed $(basename "$file")"
            fi
        done
    fi
    
    # Sign release notes if they exist
    local release_notes="$REPO_ROOT/RELEASE_NOTES_${version}.md"
    if [[ -f "$release_notes" ]]; then
        log_info "Signing release notes..."
        gpg --armor --detach-sign "$release_notes"
        log_success "Signed release notes"
    fi
}

verify_signature() {
    local version="$1"
    
    log_info "Verifying signature for tag '$version'..."
    
    # Verify the tag signature
    if git tag -v "$version" 2>&1 | grep -q "Good signature"; then
        log_success "Tag signature verified successfully"
    else
        log_error "Tag signature verification failed"
        git tag -v "$version"
        return 1
    fi
}

display_signature_info() {
    local version="$1"
    
    log_info "Signature information for '$version':"
    echo
    
    # Show tag information
    echo "Tag Information:"
    git show "$version" --format="format:%G? %GS %GK %GT" | while read -r line; do
        case "$line" in
            "G"*) echo "  Signature: Good" ;;
            "B"*) echo "  Signature: Bad" ;;
            "U"*) echo "  Signature: Unknown" ;;
            "X"*) echo "  Signature: Expired" ;;
            "Y"*) echo "  Signature: Expired" ;;
            "R"*) echo "  Signature: Revoked" ;;
            "E"*) echo "  Signature: Error" ;;
            *) echo "  $line" ;;
        esac
    done
    
    echo
    echo "GPG Key Information:"
    git show "$version" --format="format:%GK" | head -1 | xargs -I {} gpg --list-keys --keyid-format LONG {} 2>/dev/null | head -5
}

cleanup() {
    log_info "Cleaning up temporary git config..."
    # Reset git config to previous state
    git config --unset user.signingkey 2>/dev/null || true
}

# Main execution
main() {
    local version="$1"
    
    # Set up trap for cleanup
    trap cleanup EXIT
    
    log_info "Starting OmegaKG release signing process"
    log_info "Version: $version"
    echo
    
    # Prerequisites
    check_prerequisites
    
    # Validate version
    validate_version "$version"
    
    # Get GPG key
    local gpg_key
    gpg_key=$(get_gpg_key "$GPG_KEY_ID")
    
    # Sign the tag
    sign_tag "$version" "$gpg_key"
    
    # Sign release artifacts
    sign_release_artifacts "$version"
    
    # Verify signature
    verify_signature "$version"
    
    # Display signature information
    display_signature_info "$version"
    
    log_success "Release signing completed successfully!"
    log_info "The tag '$version' is now GPG-signed and ready for release"
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    if [[ $# -lt 1 ]]; then
        log_error "Version argument is required"
        usage
        exit 1
    fi
    
    main "$1"
fi