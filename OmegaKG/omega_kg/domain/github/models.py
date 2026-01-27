"""
GitHub Webhook Event Models

Pydantic models for GitHub webhook payloads, following the pattern
from omega_kg.domain.linear.models.

These models validate and parse GitHub webhook events before processing.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class GitHubRepository(BaseModel):
    """GitHub repository information."""

    name: str
    full_name: str
    owner: Dict[str, Any]


class GitHubPullRequest(BaseModel):
    """GitHub Pull Request data structure."""

    id: int
    number: int
    title: str
    merged: bool
    merge_commit_sha: Optional[str] = None
    head: Dict[str, Any] = Field(default_factory=dict)
    base: Dict[str, Any] = Field(default_factory=dict)
    html_url: Optional[str] = None
    user: Optional[Dict[str, Any]] = None


class GitHubCommit(BaseModel):
    """GitHub commit data structure."""

    sha: str
    commit: Dict[str, Any]
    html_url: Optional[str] = None


class GitHubWebhookPayload(BaseModel):
    """
    GitHub webhook payload root structure.

    This model accepts the standard GitHub webhook payload format
    for pull request events.
    """

    action: str
    pull_request: Optional[GitHubPullRequest] = None
    repository: Dict[str, Any]
    commits: Optional[List[GitHubCommit]] = None

    # Allow extra fields from GitHub
    model_config = {"extra": "allow"}


class ParsedIssueReference(BaseModel):
    """
    Parsed issue reference from commit message.

    Extracts issue identifiers from patterns like:
    - Fixes [PROJ-123]
    - Closes [LIN-456]
    - Resolves [TEAM-789]
    """

    identifier: str = Field(..., description="Issue ID, e.g., 'PROJ-123'")
    pattern: str = Field(..., description="Pattern keyword: fixes/closes/resolves")
    commit_sha: Optional[str] = Field(None, description="Commit hash if available")


class GitHubPRMergeEvent(BaseModel):
    """
    Normalized PR merge event for processing.

    Extracted and normalized data from GitHub webhook payload
    specifically for merged pull requests.
    """

    pr_number: int
    repository: str
    owner: str
    title: str
    merge_commit_sha: Optional[str] = None
    commits: List[GitHubCommit] = Field(default_factory=list)

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "GitHubPRMergeEvent":
        """
        Create PR merge event from webhook payload.

        Args:
            payload: GitHub webhook payload

        Returns:
            Normalized PR merge event

        Raises:
            ValueError: If payload is not a valid PR merge event
        """
        if payload.get("action") != "closed":
            raise ValueError("Not a closed PR event")

        pr = payload.get("pull_request", {})
        if not pr.get("merged"):
            raise ValueError("PR was not merged")

        repo = payload.get("repository", {})
        commits = payload.get("commits", [])

        return cls(
            pr_number=pr["number"],
            repository=repo["name"],
            owner=repo["owner"]["login"],
            title=pr["title"],
            merge_commit_sha=pr.get("merge_commit_sha"),
            commits=[GitHubCommit(**commit) for commit in commits],
        )
