#!/usr/bin/env python3
"""
POML-based Context Generator for ApexSigma

This script generates dynamic agent context bullets using POML templates
and real-time project data from the Master Knowledge Graph.
"""

import json
import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import poml

    POML_AVAILABLE = True
except ImportError:
    POML_AVAILABLE = False


class ContextBulletGenerator:
    """Generates agent context bullets using POML templates."""

    def __init__(self, prompts_dir: str = "prompts"):
        """Initialize the generator."""
        self.prompts_dir = Path(prompts_dir)
        self.templates = {}
        self.load_templates()

    def load_templates(self) -> None:
        """Load all POML templates from the prompts directory."""
        if not self.prompts_dir.exists():
            print(f"Warning: Prompts directory {self.prompts_dir} not found")
            return

        for poml_file in self.prompts_dir.glob("*.poml"):
            try:
                if POML_AVAILABLE:
                    template = poml.load(str(poml_file))
                    self.templates[poml_file.stem] = template
                else:
                    # Fallback: read as text
                    content = poml_file.read_text(encoding="utf-8")
                    self.templates[poml_file.stem] = content
            except Exception as e:
                print(f"Warning: Could not load template {poml_file}: {e}")

    def generate_context_bullet(
        self,
        data_source: str = None,
        output_file: str = None,
        format_type: str = "markdown",
    ) -> str:
        """Generate a complete context bullet."""

        print("=" * 80)
        print("APEXSIGMA POML CONTEXT GENERATOR")
        print("=" * 80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Templates loaded: {len(self.templates)}")
        print()

        # Load data
        context_data = self._load_context_data(data_source)

        if POML_AVAILABLE:
            content = self._generate_with_poml(context_data)
        else:
            content = self._generate_fallback(context_data)

        # Save output
        if output_file:
            output_path = Path(output_file)
            output_path.write_text(content, encoding="utf-8")
            print(f"✓ Context bullet saved to: {output_path}")
        else:
            print("GENERATED CONTEXT BULLET")
            print("-" * 40)
            print(content)

        return content

    def _load_context_data(self, data_source: str = None) -> Dict[str, Any]:
        """Load context data from various sources."""

        # Try to load from beta.ingest.as.json first
        beta_file = Path(".ingest/beta.ingest.as.json")
        if beta_file.exists():
            try:
                with open(beta_file, "r", encoding="utf-8") as f:
                    beta_data = json.load(f)

                # Transform beta data to context format
                return self._transform_beta_data(beta_data)
            except Exception as e:
                print(f"Warning: Could not load beta data: {e}")

        # Fallback to default data structure
        return self._get_default_context_data()

    def _transform_beta_data(self, beta_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform beta.ingest.as.json to context template format."""

        return {
            "timestamp": datetime.now().isoformat(),
            "session_id": f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "version": beta_data.get("ingest_metadata", {}).get("version", "1.0"),
            "mission_brief": {
                "objective": beta_data.get("mission_brief", {}).get(
                    "objective", "Continue ApexSigma development"
                ),
                "agent_roster": beta_data.get("mission_brief", {}).get(
                    "agent_roster", {}
                ),
                "embedding_service": beta_data.get("mission_brief", {})
                .get("agent_roster", {})
                .get("embedding_service", "nomic-embed-text v1.5"),
            },
            "project_status": beta_data.get("project_status", []),
            "critical_blocker": beta_data.get("critical_blocker"),
            "immediate_priorities": beta_data.get("immediate_priorities", []),
            "environment": "Local Development",
            "active_tools": ["Docker", "Poetry", "Claude Code", "POML"],
            "network_status": "Pending Docker Network Fix",
        }

    def _get_default_context_data(self) -> Dict[str, Any]:
        """Get default context data structure."""

        return {
            "timestamp": datetime.now().isoformat(),
            "session_id": f"default_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "version": "1.0",
            "mission_brief": {
                "objective": "Continue development of the ApexSigma 'Society of Agents' ecosystem",
                "agent_roster": {
                    "primary": ["Gemini CLI", "Claude Code"],
                    "support": "Local AI Models",
                    "embedding_service": "nomic-embed-text v1.5",
                },
            },
            "project_status": [
                {
                    "name": "InGest-LLM.as",
                    "status": "Active Development",
                    "details": "POML context generation system implemented",
                }
            ],
            "critical_blocker": None,
            "immediate_priorities": [
                {
                    "priority": "HIGH",
                    "task": "Implement POML Context Generation",
                    "description": "Create dynamic agent context bullets using POML templates",
                }
            ],
            "environment": "Local Development",
            "active_tools": ["Docker", "Poetry", "Claude Code", "POML"],
            "network_status": "Development Mode",
        }

    def _generate_with_poml(self, data: Dict[str, Any]) -> str:
        """Generate context using POML templates."""

        try:
            if "agent_context_template" in self.templates:
                template = self.templates["agent_context_template"]
                return template.render(**data)
            else:
                return self._generate_fallback(data)
        except Exception as e:
            print(f"POML generation failed: {e}")
            return self._generate_fallback(data)

    def _generate_fallback(self, data: Dict[str, Any]) -> str:
        """Generate context using fallback text formatting."""

        content = f"""# ApexSigma Agent Context Bullet

**Generated**: {data.get("timestamp", datetime.now().isoformat())}  
**Session ID**: {data.get("session_id", "FALLBACK")}  
**Version**: {data.get("version", "1.0")}

---

## Mission Brief

**Objective**: {data.get("mission_brief", {}).get("objective", "Continue ApexSigma development")}

**Agent Roster**:
"""

        agent_roster = data.get("mission_brief", {}).get("agent_roster", {})
        for role, agents in agent_roster.items():
            if isinstance(agents, list):
                agents_str = ", ".join(agents)
            else:
                agents_str = str(agents)
            content += f"- **{role.title()}**: {agents_str}\\n"

        content += "\\n---\\n\\n## Project Status\\n\\n"

        for project in data.get("project_status", []):
            content += f"### {project.get('name', 'Unknown Project')}\\n"
            content += f"**Status**: {project.get('status', 'Unknown')}  \\n"
            content += (
                f"**Details**: {project.get('details', 'No details available.')}\\n\\n"
            )

        # Critical blocker
        blocker = data.get("critical_blocker")
        if blocker:
            content += "---\\n\\n## ⚠️ Critical Blocker\\n\\n"
            content += f"**Issue**: {blocker.get('issue', 'Unknown issue')}  \\n"
            content += f"**Impact**: {blocker.get('impact', 'Unknown impact')}  \\n"
            content += f"**Status**: {blocker.get('status', 'Unknown status')}\\n\\n"

        # Priorities
        content += "---\\n\\n## Immediate Priorities\\n\\n"

        for task in data.get("immediate_priorities", []):
            content += f"### {task.get('priority', 'UNKNOWN')}: {task.get('task', 'Unknown Task')}\\n"
            if task.get("project"):
                content += f"**Project**: {task['project']}  \\n"
            content += f"**Description**: {task.get('description', 'No description available.')}\\n\\n"

        # Development context
        content += (
            """---

## Development Context

**Environment**: """
            + data.get("environment", "Local Development")
            + """  
**Tools Active**: """
            + ", ".join(data.get("active_tools", []))
            + """  
**Network Status**: """
            + data.get("network_status", "Unknown")
            + """

## Success Metrics

- [ ] Critical blockers resolved
- [ ] High-priority tasks advanced
- [ ] Integration tests passing
- [ ] Documentation updated

---

*This context bullet was automatically generated using POML templates and real-time project data.*"""
        )

        return content

    def list_templates(self) -> None:
        """List all available POML templates."""

        print("AVAILABLE POML TEMPLATES")
        print("-" * 30)

        if not self.templates:
            print("No templates found")
            return

        for name, template in self.templates.items():
            print(f"✓ {name}.poml")
            if hasattr(template, "metadata"):
                desc = template.metadata.get("description", "No description")
                print(f"    {desc}")

        print(f"\\nTotal templates: {len(self.templates)}")

    def validate_templates(self) -> bool:
        """Validate all POML templates."""

        print("VALIDATING POML TEMPLATES")
        print("-" * 30)

        valid_count = 0
        total_count = len(self.templates)

        for name, template in self.templates.items():
            try:
                if POML_AVAILABLE and hasattr(template, "validate"):
                    template.validate()
                print(f"✓ {name}.poml - Valid")
                valid_count += 1
            except Exception as e:
                print(f"✗ {name}.poml - Error: {e}")

        print(f"\\nValidation complete: {valid_count}/{total_count} templates valid")
        return valid_count == total_count


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description="Generate dynamic agent context bullets using POML",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_context_bullet.py                           # Generate using beta data
  python generate_context_bullet.py --output context.md       # Save to file
  python generate_context_bullet.py --list-templates          # List templates
  python generate_context_bullet.py --validate                # Validate templates
        """,
    )

    parser.add_argument(
        "--output", metavar="FILE", help="Output file path (default: print to console)"
    )

    parser.add_argument(
        "--data-source",
        metavar="FILE",
        help="Custom data source file (default: .ingest/beta.ingest.as.json)",
    )

    parser.add_argument(
        "--list-templates",
        action="store_true",
        help="List all available POML templates",
    )

    parser.add_argument(
        "--validate", action="store_true", help="Validate all POML templates"
    )

    parser.add_argument(
        "--format",
        choices=["markdown", "json", "text"],
        default="markdown",
        help="Output format (default: markdown)",
    )

    args = parser.parse_args()

    # Create generator
    generator = ContextBulletGenerator()

    if args.list_templates:
        generator.list_templates()
        return

    if args.validate:
        valid = generator.validate_templates()
        sys.exit(0 if valid else 1)

    # Generate context bullet
    try:
        generator.generate_context_bullet(
            data_source=args.data_source,
            output_file=args.output,
            format_type=args.format,
        )
        print("\\n✓ Context generation completed successfully!")

    except Exception as e:
        print(f"\\nError: Context generation failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    if not POML_AVAILABLE:
        print("Warning: POML library not available, using fallback generation")
        print("Install with: poetry add poml")
        print()

    main()
