"""
Unit tests for UID extraction from markdown files
"""

import frontmatter


def test_uid_extraction_from_markdown(tmp_path):
    """Test that UIDs can be extracted from markdown frontmatter"""
    # Create a temporary markdown file with frontmatter
    md_file = tmp_path / "test_task.md"
    content = """---
uid: DRAFT-001
title: Test Task
status: draft
---

# Test Task

This is a test task.
"""

    md_file.write_text(content)

    # Load and extract UID
    post = frontmatter.load(str(md_file))
    uid = post.metadata.get("uid")

    assert uid == "DRAFT-001"


def test_uid_extraction_missing_uid(tmp_path):
    """Test behavior when UID is missing from frontmatter"""
    # Create a temporary markdown file without UID
    md_file = tmp_path / "test_task_no_uid.md"
    content = """---
title: Test Task Without UID
status: draft
---

# Test Task Without UID

This task has no UID.
"""

    md_file.write_text(content)

    # Load and check UID extraction
    post = frontmatter.load(str(md_file))
    uid = post.metadata.get("uid", "NONE")

    assert uid == "NONE"
