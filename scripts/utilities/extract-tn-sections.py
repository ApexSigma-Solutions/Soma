#!/usr/bin/env python3
"""
Script to extract individual Technical Notes (TN-PAR-501 to TN-PAR-505)
from a combined markdown file and save each as a separate file.

Usage:
    python scripts/extract_tn_sections.py [--source <source_file>] [--output <output_dir>]
"""

import argparse
import re
import sys
from pathlib import Path


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Extract individual TN sections from combined markdown file"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="OmegaVault/TN/TN-PAR-501 to 505.md",
        help="Path to the source markdown file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="OmegaVault/TN/",
        help="Output directory for extracted files",
    )
    return parser.parse_args()


def extract_sections(content: str) -> dict[str, str]:
    """
    Extract individual TN sections from the combined content.

    Args:
        content: The raw markdown content containing multiple TN sections

    Returns:
        Dictionary mapping TN IDs (e.g., 'TN-PAR-501') to their full content
    """
    sections: dict[str, str] = {}

    # Split by the delimiter
    raw_sections = content.split("---TASK-NOTE-DELIMITER---")

    for raw_section in raw_sections:
        raw_section = raw_section.strip()
        if not raw_section:
            continue

        # Remove any leading metadata block (--- ... ---) that appears before the first TN
        # This handles files that have outer file metadata before the first TN
        content_to_parse = raw_section
        if "```markdown" in raw_section:
            # Content starts with markdown code block, extract inner content
            match = re.search(r"```markdown\n(.*)", raw_section, re.DOTALL)
            if match:
                content_to_parse = match.group(1).strip()

        # Extract the uid from the YAML frontmatter
        # Look for pattern: uid: TN-PAR-XXX
        uid_match = re.search(r"^uid:\s*(TN-PAR-\d+)", content_to_parse, re.MULTILINE)

        if uid_match:
            tn_id = uid_match.group(1)
            sections[tn_id] = raw_section
            print(f"  Found section: {tn_id}")
        else:
            # Try to find TN-PAR in content if no uid found
            tn_match = re.search(r"(TN-PAR-\d+)", content_to_parse)
            if tn_match:
                tn_id = tn_match.group(1)
                sections[tn_id] = raw_section
                print(f"  Found section by content: {tn_id}")

    return sections


def save_sections(
    sections: dict[str, str], output_dir: Path, source_file: Path
) -> dict[str, Path]:
    """
    Save extracted sections to individual files.

    Args:
        sections: Dictionary mapping TN IDs to their content
        output_dir: Directory to save output files
        source_file: Original source file path (for relative path comments)

    Returns:
        Dictionary mapping TN IDs to their output file paths
    """
    output_paths: dict[str, Path] = {}
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Expected TN sections to extract
    expected_tns = [
        "TN-PAR-501",
        "TN-PAR-502",
        "TN-PAR-503",
        "TN-PAR-504",
        "TN-PAR-505",
    ]

    for tn_id in expected_tns:
        if tn_id in sections:
            content = sections[tn_id]
            output_file = output_dir / f"{tn_id}.md"
            output_file.write_text(content, encoding="utf-8")
            output_paths[tn_id] = output_file
            print(f"  Saved: {output_file}")
        else:
            print(f"  Warning: {tn_id} not found in source file")

    return output_paths


def add_source_reference(content: str, source_file: Path) -> str:
    """
    Add a source file reference comment at the top of the content.

    Args:
        content: The section content
        source_file: The original source file path

    Returns:
        Content with source reference added
    """
    source_comment = f"<!-- Extracted from: {source_file} -->\n\n"
    return source_comment + content


def main() -> int:
    """Main entry point for the extraction script."""
    args = parse_arguments()

    source_file = Path(args.source)
    output_dir = Path(args.output)

    print(f"Source file: {source_file}")
    print(f"Output directory: {output_dir}")
    print()

    # Check if source file exists
    if not source_file.exists():
        print(f"Error: Source file not found: {source_file}", file=sys.stderr)
        return 1

    # Read source file
    print("Reading source file...")
    content = source_file.read_text(encoding="utf-8")
    print(f"  Read {len(content)} characters")
    print()

    # Extract sections
    print("Extracting TN sections...")
    sections = extract_sections(content)
    print(f"  Found {len(sections)} sections")
    print()

    # Save sections
    print("Saving extracted sections...")
    output_paths = save_sections(sections, output_dir, source_file)
    print()

    # Summary
    print("Summary:")
    print("-" * 40)
    for tn_id, path in output_paths.items():
        print(f"  {tn_id}: {path}")

    if len(output_paths) < 5:
        print(f"\nNote: Only {len(output_paths)} of 5 expected sections found.")
        print("TN-PAR-505 may not be present in the source file.")

    print("\nExtraction complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
