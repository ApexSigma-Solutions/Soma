"""
Test fixtures for GitHub webhook payloads.

Sample GitHub webhook events for testing the webhook receiver
and event processor.
"""

# Standard PR merge event with single issue reference
PR_MERGED_SINGLE_ISSUE = {
    "action": "closed",
    "pull_request": {
        "id": 1234567890,
        "number": 42,
        "title": "Fixes [PROJ-123] - Add authentication fix",
        "merged": True,
        "merge_commit_sha": "abc123def456789",
        "head": {
            "sha": "abc123def456789",
            "ref": "feature/auth-fix",
        },
        "base": {
            "ref": "main",
        },
        "html_url": "https://github.com/user/repo/pull/42",
        "user": {
            "login": "developer",
            "id": 12345,
        },
    },
    "repository": {
        "id": 123456789,
        "name": "repo",
        "full_name": "user/repo",
        "owner": {
            "login": "user",
            "id": 67890,
        },
        "html_url": "https://github.com/user/repo",
    },
    "sender": {
        "login": "user",
        "id": 67890,
    },
}

# PR merge event with multiple issue references
PR_MERGED_MULTIPLE_ISSUES = {
    "action": "closed",
    "pull_request": {
        "id": 1234567890,
        "number": 43,
        "title": "Multi-issue PR: Fixes [PROJ-123] and [LIN-456]",
        "merged": True,
        "merge_commit_sha": "def456ghi012",
        "head": {
            "sha": "def456ghi012",
            "ref": "feature/multi-fix",
        },
        "base": {
            "ref": "main",
        },
        "html_url": "https://github.com/user/repo/pull/43",
    },
    "repository": {
        "id": 123456789,
        "name": "repo",
        "full_name": "user/repo",
        "owner": {
            "login": "user",
            "id": 67890,
        },
    },
}

# PR closed but not merged
PR_CLOSED_NOT_MERGED = {
    "action": "closed",
    "pull_request": {
        "id": 1234567890,
        "number": 44,
        "title": "Draft feature",
        "merged": False,
        "merge_commit_sha": None,
        "head": {
            "sha": "ghi789jkl012",
            "ref": "feature/draft",
        },
        "base": {
            "ref": "main",
        },
        "html_url": "https://github.com/user/repo/pull/44",
    },
    "repository": {
        "id": 123456789,
        "name": "repo",
        "full_name": "user/repo",
        "owner": {
            "login": "user",
            "id": 67890,
        },
    },
}

# PR opened (not closed)
PR_OPENED = {
    "action": "opened",
    "pull_request": {
        "id": 1234567890,
        "number": 45,
        "title": "New feature",
        "merged": False,
        "merge_commit_sha": None,
        "head": {
            "sha": "jkl012mno345",
            "ref": "feature/new",
        },
        "base": {
            "ref": "main",
        },
        "html_url": "https://github.com/user/repo/pull/45",
    },
    "repository": {
        "id": 123456789,
        "name": "repo",
        "full_name": "user/repo",
        "owner": {
            "login": "user",
            "id": 67890,
        },
    },
}

# PR merged with "Closes" keyword
PR_MERGED_CLOSES = {
    "action": "closed",
    "pull_request": {
        "id": 1234567890,
        "number": 46,
        "title": "Closes [LIN-456] - Resolve API issue",
        "merged": True,
        "merge_commit_sha": "mno345pqr678",
        "head": {
            "sha": "mno345pqr678",
            "ref": "feature/api-fix",
        },
        "base": {
            "ref": "main",
        },
        "html_url": "https://github.com/user/repo/pull/46",
    },
    "repository": {
        "id": 123456789,
        "name": "repo",
        "full_name": "user/repo",
        "owner": {
            "login": "user",
            "id": 67890,
        },
    },
}

# PR merged with "Resolves" keyword
PR_MERGED_RESOLVES = {
    "action": "closed",
    "pull_request": {
        "id": 1234567890,
        "number": 47,
        "title": "Resolves [TEAM-789] - Update documentation",
        "merged": True,
        "merge_commit_sha": "pqr678stu901",
        "head": {
            "sha": "pqr678stu901",
            "ref": "feature/docs-update",
        },
        "base": {
            "ref": "main",
        },
        "html_url": "https://github.com/user/repo/pull/47",
    },
    "repository": {
        "id": 123456789,
        "name": "repo",
        "full_name": "user/repo",
        "owner": {
            "login": "user",
            "id": 67890,
        },
    },
}

# PR merged with no issue references
PR_MERGED_NO_REFERENCES = {
    "action": "closed",
    "pull_request": {
        "id": 1234567890,
        "number": 48,
        "title": "Update README with new instructions",
        "merged": True,
        "merge_commit_sha": "stu901vwx234",
        "head": {
            "sha": "stu901vwx234",
            "ref": "feature/readme",
        },
        "base": {
            "ref": "main",
        },
        "html_url": "https://github.com/user/repo/pull/48",
    },
    "repository": {
        "id": 123456789,
        "name": "repo",
        "full_name": "user/repo",
        "owner": {
            "login": "user",
            "id": 67890,
        },
    },
}

# Sample commits from PR with issue references
PR_COMMITS_WITH_REFERENCES = [
    {
        "sha": "abc123def456",
        "commit": {
            "message": "Fixes [PROJ-123] - Add authentication fix\n\n- Implement JWT validation\n- Add session management\n- Fix security vulnerability",
            "author": {
                "name": "Developer",
                "email": "dev@example.com",
                "date": "2024-01-01T12:00:00Z",
            },
        },
        "html_url": "https://github.com/user/repo/commit/abc123def456",
    },
    {
        "sha": "789ghi012jkl",
        "commit": {
            "message": "Closes [LIN-456] - Update API endpoints\n\n- Add new endpoint\n- Update documentation",
            "author": {
                "name": "Developer",
                "email": "dev@example.com",
                "date": "2024-01-02T12:00:00Z",
            },
        },
        "html_url": "https://github.com/user/repo/commit/789ghi012jkl",
    },
]

# Sample commits without issue references
PR_COMMITS_NO_REFERENCES = [
    {
        "sha": "abc123def456",
        "commit": {
            "message": "Update README with installation instructions\n\n- Add prerequisites\n- Update examples",
            "author": {
                "name": "Developer",
                "email": "dev@example.com",
                "date": "2024-01-01T12:00:00Z",
            },
        },
        "html_url": "https://github.com/user/repo/commit/abc123def456",
    },
]

# GitHub API responses
GITHUB_PR_RESPONSE = {
    "id": 1234567890,
    "number": 42,
    "title": "Fixes [PROJ-123] - Add authentication fix",
    "state": "closed",
    "merged": True,
    "merge_commit_sha": "abc123def456789",
    "head": {
        "sha": "abc123def456789",
        "ref": "feature/auth-fix",
    },
    "base": {
        "ref": "main",
    },
    "html_url": "https://github.com/user/repo/pull/42",
    "user": {
        "login": "developer",
        "id": 12345,
    },
}

GITHUB_PR_COMMITS_RESPONSE = [
    {
        "sha": "abc123def456",
        "commit": {
            "message": "Fixes [PROJ-123] - Add authentication fix",
            "author": {
                "name": "Developer",
                "email": "dev@example.com",
                "date": "2024-01-01T12:00:00Z",
            },
        },
        "html_url": "https://github.com/user/repo/commit/abc123def456",
    },
]
