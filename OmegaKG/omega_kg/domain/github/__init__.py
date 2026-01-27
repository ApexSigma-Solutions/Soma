"""
GitHub Integration Domain

This module handles GitHub webhook events and integrates them with
the OmegaKG system, specifically for PR → Linear → Obsidian automation.
"""

from .processor import get_github_processor, GitHubProcessor

__all__ = ["get_github_processor", "GitHubProcessor"]
