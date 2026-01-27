"""
Linear to Obsidian Mapper

Converts Linear Issue domain models to Obsidian markdown format.
"""

import re
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
from bs4 import BeautifulSoup

from omega_kg.domain.linear.models import LinearIssue

logger = logging.getLogger(__name__)


class LinearToObsidianMapper:
    """
    Maps Linear Issues to Obsidian markdown files.

    Responsibilities:
    - Generate frontmatter from Linear metadata
    - Convert HTML description to Markdown
    - Sanitize filenames
    """

    # State type to Obsidian status mapping
    STATE_MAPPING = {
        "started": "In Progress",
        "completed": "Completed",
        "canceled": "Archived",
        "triage": "Draft",
        "backlog": "Draft",
        "unstarted": "Draft",
    }

    # Priority to tag mapping
    PRIORITY_TAGS = {
        0: "priority/none",
        1: "priority/urgent",
        2: "priority/high",
        3: "priority/medium",
        4: "priority/low",
    }

    def __init__(self, vault_path: Path):
        """
        Initialize mapper with vault path.

        Args:
            vault_path: Root path of Obsidian vault
        """
        self.vault_path = Path(vault_path)

    def map_issue_to_markdown(self, issue: LinearIssue) -> Tuple[Path, str]:
        """
        Convert Linear Issue to Obsidian markdown format.

        Args:
            issue: LinearIssue domain model

        Returns:
            Tuple of (file_path, markdown_content)
        """
        # Generate frontmatter
        frontmatter = self._generate_frontmatter(issue)

        # Convert description to markdown
        body = self._convert_description(issue.description)

        # Build full markdown
        markdown_content = self._build_markdown(frontmatter, issue.title, body)

        # Generate filename
        file_path = self._generate_filename(issue)

        return file_path, markdown_content

    def map_issue_to_tnp(
        self, issue: LinearIssue, template_path: Path
    ) -> Tuple[Path, str]:
        """
        Convert Linear Issue to Task Note Plan (.tnp.md) format.

        Args:
            issue: LinearIssue domain model
            template_path: Path to the .tnp.md template

        Returns:
            Tuple of (file_path, markdown_content)
        """
        if not template_path.exists():
            logger.warning(f"TNP template not found at {template_path}")
            # Fallback to a very basic structure if template is missing
            template_content = (
                "## 1. High-Level Objective\n\n"
                '## 2. "Done Means Done" Criteria\n\n'
                "## 3. Task Breakdown\n\n"
                "## 4. Notes & Context"
            )
        else:
            template_content = template_path.read_text(encoding="utf-8")

        # Map fields to template
        content = self._fill_tnp_template(template_content, issue)

        # Generate filename
        file_path = self._generate_tnp_filename(issue)

        return file_path, content

    def _generate_tnp_filename(self, issue: LinearIssue) -> Path:
        """
        Generate sanitized filename for TNP file.

        Format: TNP-XXX-000-Title.tnp.md or [IDENTIFIER] Title.tnp.md (legacy)
        """
        # Check if using TNP prefix naming convention (from uid)
        if issue.identifier and "-" in issue.identifier:
            # Use TNP prefix format from identifier
            parts = issue.identifier.split("-")
            if len(parts) >= 2:
                # Extract prefix and number from identifier like APX-123
                prefix = parts[0]
                num = "-".join(parts[1:]) if len(parts) > 2 else parts[1]
                sanitized_title = self._sanitize_filename(issue.title)
                filename = f"TNP-{prefix}-{num}-{sanitized_title}.tnp.md"
                return self.vault_path / "TNP" / filename

        # Fallback to legacy format
        sanitized_title = self._sanitize_filename(issue.title)
        filename = f"[{issue.identifier}] {sanitized_title}.tnp.md"
        return self.vault_path / "Linear" / filename

    def _fill_tnp_template(self, template: str, issue: LinearIssue) -> str:
        """
        Fill the TNP template with issue data.
        """
        # 1. Objective
        objective = issue.title

        # 3. Task Breakdown
        tasks = []
        if issue.children:
            for child in issue.children:
                status = "x" if child.state and child.state.type == "completed" else " "
                tasks.append(f"- [{status}] [{child.identifier}] {child.title}")
        else:
            tasks.append("- [ ] ")

        task_breakdown = "\n".join(tasks)

        # 4. Notes & Context
        notes_parts = []
        if issue.url:
            notes_parts.append(f"Linear URL: {issue.url}")
        if issue.description:
            notes_parts.append(self._convert_description(issue.description))

        notes = "\n\n".join(notes_parts)

        # Replacement logic using regex to find sections
        content = template

        # Replace Objective section (after header until next header)
        content = re.sub(
            r"(## 1\. High-Level Objective\n\n).*?(\n\n## 2\.)",
            lambda m: f"{m.group(1)}{objective}{m.group(2)}",
            content,
            flags=re.DOTALL,
        )

        # Replace Task Breakdown section
        # We keep the "This is the granular..." instruction if it exists
        instruction = "This is the granular, tactical list of work. **Every task here MUST use the `- [ ]` or `- [x]` syntax.**"
        content = re.sub(
            r"(## 3\. Task Breakdown\n\n).*?(\n\n## 4\.)",
            lambda m: f"{m.group(1)}{instruction}\n\n{task_breakdown}{m.group(2)}",
            content,
            flags=re.DOTALL,
        )

        # Replace Notes & Context section (until end of file)
        content = re.sub(
            r"(## 4\. Notes & Context\n\n).*",
            lambda m: f"{m.group(1)}{notes}",
            content,
            flags=re.DOTALL,
        )

        return content

    def _generate_frontmatter(self, issue: LinearIssue) -> Dict[str, Any]:
        """
        Generate frontmatter dict from Linear Issue.

        Args:
            issue: LinearIssue domain model

        Returns:
            Frontmatter dict
        """
        frontmatter: Dict[str, Any] = {
            "linear_id": issue.id,
            "identifier": issue.identifier,
            "status": self._map_state(issue.state.type if issue.state else None),
            "tags": self._generate_tags(issue),
        }

        # Add optional fields
        if issue.priority is not None:
            frontmatter["priority"] = issue.priority

        if issue.assignee:
            frontmatter["assignee"] = issue.assignee.name or issue.assignee.email

        if issue.createdAt:
            frontmatter["created"] = issue.createdAt.isoformat()

        if issue.updatedAt:
            frontmatter["updated"] = issue.updatedAt.isoformat()

        return frontmatter

    def _map_state(self, state_type: str | None) -> str:
        """
        Map Linear state type to Obsidian status.

        Args:
            state_type: Linear state type (e.g., "started", "completed")

        Returns:
            Obsidian status string
        """
        if not state_type:
            return "Draft"
        return self.STATE_MAPPING.get(state_type.lower(), "Draft")

    def _generate_tags(self, issue: LinearIssue) -> list[str]:
        """
        Generate tag list from Linear Issue.

        Args:
            issue: LinearIssue domain model

        Returns:
            List of tag strings
        """
        tags = ["linear"]

        # Add priority tag
        priority_tag = self.PRIORITY_TAGS.get(issue.priority or 0)
        if priority_tag:
            tags.append(priority_tag)

        # Add label tags
        for label in issue.labels:
            # Sanitize label name for Obsidian tags
            tag = self._sanitize_tag(label.name)
            if tag:
                tags.append(tag)

        return tags

    def _sanitize_tag(self, tag: str) -> str:
        """
        Sanitize tag name for Obsidian.

        Args:
            tag: Raw tag string

        Returns:
            Sanitized tag string
        """
        # Replace spaces and special chars with hyphens
        tag = re.sub(r"[^\w\s-]", "", tag)
        tag = re.sub(r"[\s_]+", "-", tag)
        return tag.lower().strip("-")

    def _convert_description(self, description: str | None) -> str:
        """
        Convert HTML description to Markdown.

        Args:
            description: HTML description from Linear

        Returns:
            Markdown formatted string
        """
        if not description:
            return ""

        # Parse HTML
        soup = BeautifulSoup(description, "html.parser")

        # Convert to text (basic conversion)
        # For production, consider using html2text or markdownify
        text = soup.get_text(separator="\n\n")

        return text.strip()

    def _build_markdown(
        self, frontmatter: Dict[str, Any], title: str, body: str
    ) -> str:
        """
        Build complete markdown file content.

        Args:
            frontmatter: Frontmatter dict
            title: Issue title
            body: Markdown body

        Returns:
            Complete markdown string with frontmatter
        """
        import yaml

        # Build frontmatter YAML
        fm_yaml = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)

        # Build markdown
        markdown = f"---\n{fm_yaml}---\n\n# {title}\n\n{body}"

        return markdown

    def _generate_filename(self, issue: LinearIssue) -> Path:
        """
        Generate sanitized filename for issue.

        Format: [IDENTIFIER] Title.md
        Example: [APX-123] Implement Linear Sync.md

        Args:
            issue: LinearIssue domain model

        Returns:
            Path relative to vault root
        """
        # Sanitize title
        sanitized_title = self._sanitize_filename(issue.title)

        # Build filename
        filename = f"[{issue.identifier}] {sanitized_title}.md"

        # Use Linear subdirectory in vault
        file_path = self.vault_path / "Linear" / filename

        return file_path

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize string for use in filename.

        Args:
            filename: Raw filename string

        Returns:
            Sanitized filename string
        """
        # Remove invalid filename characters
        filename = re.sub(r'[<>:"/\\|?*]', "", filename)

        # Collapse multiple spaces
        filename = re.sub(r"\s+", " ", filename)

        # Limit length (Windows has 255 char limit)
        # Truncate at UTF-8 byte boundary to prevent Unicode corruption
        max_length = 100
        filename_bytes = filename.encode("utf-8")
        if len(filename_bytes) > max_length:
            # Truncate bytes and decode, ignoring incomplete characters
            filename = filename_bytes[:max_length].decode("utf-8", "ignore").strip()

        return filename.strip()
