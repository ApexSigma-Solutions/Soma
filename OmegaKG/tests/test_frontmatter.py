from pathlib import Path

import frontmatter

from omega_kg.settings import Settings


def test_frontmatter_extraction():
    settings = Settings()
    vault_path = Path(settings.obsidian_vault_path)
    task_files = list(vault_path.glob("Tasks/*.md"))

    print(f"Found {len(task_files)} task files")

    for task_file in task_files[:2]:
        print(f"\n--- {task_file.name} ---")
        post = frontmatter.load(task_file)
        print(f"Metadata: {post.metadata}")
        print(f"UID: {post.metadata.get('uid')}")
        print(f"Title: {post.metadata.get('title', task_file.stem)}")
        print(f"Status: {post.metadata.get('status', 'draft')}")


if __name__ == "__main__":
    test_frontmatter_extraction()
