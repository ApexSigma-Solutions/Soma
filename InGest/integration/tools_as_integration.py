"""
Tools.as Integration for Ecosystem Ingestion

This module provides integration utilities for adding ecosystem ingestion
to the tools.as EOD (End of Day) command workflow.
"""

import json
from pathlib import Path
from typing import Dict, Any


def generate_eod_command_config() -> Dict[str, Any]:
    """
    Generate the tools.as command configuration for ecosystem EOD updates.

    Returns:
        Dict[str, Any]: Command configuration for tools.as
    """

    command_config = {
        "name": "eod-ecosystem",
        "description": "End of Day ecosystem update with comprehensive codebase ingestion",
        "version": "1.0.0",
        "category": "ecosystem",
        "tags": ["eod", "ecosystem", "ingestion", "apexsigma"],
        "command": {
            "type": "python_script",
            "script_path": "C:\\Users\\steyn\\ApexSigmaProjects.Dev\\InGest-LLM.as\\scripts\\eod_ecosystem_update.py",
            "working_directory": "C:\\Users\\steyn\\ApexSigmaProjects.Dev\\InGest-LLM.as",
            "environment": "poetry",
            "timeout_minutes": 30,
        },
        "parameters": {
            "force": {
                "type": "boolean",
                "default": False,
                "description": "Force refresh even if recent snapshots exist",
                "flag": "--force",
            },
            "no_historical": {
                "type": "boolean",
                "default": False,
                "description": "Skip storing historical snapshots in memOS",
                "flag": "--no-historical",
            },
            "report_only": {
                "type": "boolean",
                "default": False,
                "description": "Generate daily report without full ingestion",
                "flag": "--report-only",
            },
        },
        "scheduling": {
            "daily": {
                "time": "18:00",
                "description": "Daily ecosystem snapshot at 6 PM",
            },
            "weekly": {
                "day": "sunday",
                "time": "19:00",
                "parameters": {"force": True},
                "description": "Weekly comprehensive ecosystem analysis",
            },
        },
        "outputs": {
            "ecosystem_snapshot": {
                "type": "json",
                "description": "Complete ecosystem analysis snapshot",
                "storage": "memOS.as",
            },
            "daily_report": {
                "type": "markdown",
                "description": "Human-readable daily ecosystem report",
                "storage": "local_files",
            },
            "health_metrics": {
                "type": "metrics",
                "description": "Ecosystem health and performance metrics",
                "storage": "prometheus",
            },
        },
        "dependencies": {
            "services": ["InGest-LLM.as", "memOS.as"],
            "external": ["LM Studio", "Langfuse"],
            "optional": ["Prometheus", "Grafana"],
        },
        "monitoring": {
            "success_criteria": [
                "All 4 projects successfully processed",
                "Ecosystem health score > 0.7",
                "Historical snapshot stored in memOS",
            ],
            "failure_recovery": [
                "Retry with --force flag",
                "Check service dependencies",
                "Verify memOS connectivity",
            ],
            "notifications": {
                "success": "Log ecosystem health score and project count",
                "failure": "Alert if ecosystem health degrades significantly",
                "warnings": "Notify if individual project processing fails",
            },
        },
        "integration": {
            "memOS": {
                "memory_tiers": ["semantic", "episodic"],
                "metadata_tags": ["ecosystem", "daily_snapshot", "eod"],
                "retention_policy": "semantic: permanent, episodic: 30 days",
            },
            "observability": {
                "langfuse_tracing": True,
                "prometheus_metrics": True,
                "structured_logging": True,
            },
        },
    }

    return command_config


def generate_ecosystem_workflow_config() -> Dict[str, Any]:
    """
    Generate workflow configuration for comprehensive ecosystem management.

    Returns:
        Dict[str, Any]: Workflow configuration
    """

    workflow_config = {
        "name": "ecosystem_management",
        "description": "Comprehensive ApexSigma ecosystem management workflow",
        "version": "1.0.0",
        "stages": [
            {
                "name": "morning_health_check",
                "description": "Morning ecosystem health assessment",
                "schedule": "daily 09:00",
                "command": "eod-ecosystem",
                "parameters": {"report_only": True},
                "success_criteria": ["Health report generated"],
                "on_failure": "notify_team",
            },
            {
                "name": "development_snapshot",
                "description": "Mid-day development snapshot for active projects",
                "schedule": "daily 14:00",
                "command": "ingest-repository",
                "targets": ["current_active_project"],
                "parameters": {"include_embeddings": True},
                "conditional": "if development activity detected",
            },
            {
                "name": "eod_comprehensive_update",
                "description": "End of day comprehensive ecosystem update",
                "schedule": "daily 18:00",
                "command": "eod-ecosystem",
                "parameters": {"force": False, "include_historical": True},
                "success_criteria": [
                    "All projects processed",
                    "Historical snapshots stored",
                    "Health metrics updated",
                ],
                "on_success": "update_team_dashboard",
                "on_failure": "escalate_to_maintainer",
            },
            {
                "name": "weekly_deep_analysis",
                "description": "Weekly comprehensive analysis with comparisons",
                "schedule": "weekly sunday 19:00",
                "command": "eod-ecosystem",
                "parameters": {"force": True, "deep_analysis": True},
                "additional_steps": [
                    "generate_weekly_comparison_report",
                    "analyze_growth_trends",
                    "update_architecture_documentation",
                ],
            },
        ],
        "notifications": {
            "channels": ["slack", "email", "dashboard"],
            "escalation": {
                "warning": "maintainer",
                "critical": "team_lead + maintainer",
                "system_failure": "all_stakeholders",
            },
        },
        "data_retention": {
            "daily_snapshots": "30 days",
            "weekly_snapshots": "1 year",
            "monthly_snapshots": "permanent",
            "health_metrics": "1 year",
            "error_logs": "90 days",
        },
    }

    return workflow_config


def create_tools_as_integration_files(output_dir: str = "integration_configs") -> None:
    """
    Create integration configuration files for tools.as.

    Args:
        output_dir: Directory to store integration files
    """

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Generate command configuration
    eod_config = generate_eod_command_config()
    eod_config_path = output_path / "eod_ecosystem_command.json"

    with open(eod_config_path, "w", encoding="utf-8") as f:
        json.dump(eod_config, f, indent=2)

    print(f"✅ EOD command configuration: {eod_config_path}")

    # Generate workflow configuration
    workflow_config = generate_ecosystem_workflow_config()
    workflow_config_path = output_path / "ecosystem_workflow.json"

    with open(workflow_config_path, "w", encoding="utf-8") as f:
        json.dump(workflow_config, f, indent=2)

    print(f"✅ Workflow configuration: {workflow_config_path}")

    # Generate tools.as TOML command file
    toml_config = generate_tools_as_toml()
    toml_config_path = output_path / "eod_ecosystem.command.as.toml"

    with open(toml_config_path, "w", encoding="utf-8") as f:
        f.write(toml_config)

    print(f"✅ Tools.as TOML command: {toml_config_path}")

    # Generate README for integration
    readme_content = generate_integration_readme()
    readme_path = output_path / "README.md"

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"✅ Integration documentation: {readme_path}")


def generate_tools_as_toml() -> str:
    """Generate tools.as compatible TOML command configuration."""

    toml_config = """# ApexSigma Ecosystem EOD Command Configuration
# This file integrates ecosystem ingestion into the tools.as command system

[command]
name = "eod-ecosystem"
description = "End of Day ecosystem update with comprehensive codebase ingestion"
version = "1.0.0"
category = "ecosystem"
tags = ["eod", "ecosystem", "ingestion", "apexsigma"]

[command.execution]
type = "python_script"
script_path = "C:\\\\Users\\\\steyn\\\\ApexSigmaProjects.Dev\\\\InGest-LLM.as\\\\scripts\\\\eod_ecosystem_update.py"
working_directory = "C:\\\\Users\\\\steyn\\\\ApexSigmaProjects.Dev\\\\InGest-LLM.as"
environment = "poetry"
timeout_minutes = 30

[command.parameters]
force = { type = "boolean", default = false, flag = "--force", description = "Force refresh even if recent snapshots exist" }
no_historical = { type = "boolean", default = false, flag = "--no-historical", description = "Skip storing historical snapshots" }
report_only = { type = "boolean", default = false, flag = "--report-only", description = "Generate report without full ingestion" }

[command.scheduling]
[command.scheduling.daily]
time = "18:00"
description = "Daily ecosystem snapshot at 6 PM"

[command.scheduling.weekly]
day = "sunday"
time = "19:00"
parameters = { force = true }
description = "Weekly comprehensive ecosystem analysis"

[command.outputs]
[command.outputs.ecosystem_snapshot]
type = "json"
description = "Complete ecosystem analysis snapshot"
storage = "memOS.as"

[command.outputs.daily_report]
type = "markdown" 
description = "Human-readable daily ecosystem report"
storage = "local_files"

[command.outputs.health_metrics]
type = "metrics"
description = "Ecosystem health and performance metrics"
storage = "prometheus"

[command.dependencies]
services = ["InGest-LLM.as", "memOS.as"]
external = ["LM Studio", "Langfuse"]
optional = ["Prometheus", "Grafana"]

[command.monitoring]
success_criteria = [
    "All 4 projects successfully processed",
    "Ecosystem health score > 0.7", 
    "Historical snapshot stored in memOS"
]
failure_recovery = [
    "Retry with --force flag",
    "Check service dependencies",
    "Verify memOS connectivity"
]

[command.monitoring.notifications]
success = "Log ecosystem health score and project count"
failure = "Alert if ecosystem health degrades significantly"
warnings = "Notify if individual project processing fails"

[command.integration]
[command.integration.memOS]
memory_tiers = ["semantic", "episodic"]
metadata_tags = ["ecosystem", "daily_snapshot", "eod"]
retention_policy = "semantic: permanent, episodic: 30 days"

[command.integration.observability]
langfuse_tracing = true
prometheus_metrics = true
structured_logging = true
"""

    return toml_config


def generate_integration_readme() -> str:
    """Generate README for tools.as integration."""

    readme_content = """# Tools.as Integration for Ecosystem Ingestion

This directory contains configuration files for integrating ApexSigma ecosystem ingestion into the tools.as command system.

## Files

### eod_ecosystem_command.json
Complete command configuration in JSON format for programmatic integration.

### ecosystem_workflow.json  
Workflow configuration defining the complete ecosystem management lifecycle.

### eod_ecosystem.command.as.toml
Tools.as compatible TOML command configuration file.

## Integration Steps

1. **Copy Command Configuration**
   ```bash
   cp eod_ecosystem.command.as.toml /path/to/tools.as/commands/
   ```

2. **Update tools.as Configuration**
   Add the ecosystem command to your tools.as command registry.

3. **Verify Dependencies**
   Ensure InGest-LLM.as and memOS.as services are running and accessible.

4. **Test the Integration**
   ```bash
   tools.as run eod-ecosystem --report-only
   ```

## Usage Examples

### Standard EOD Update
```bash
tools.as run eod-ecosystem
```

### Force Refresh All Projects
```bash  
tools.as run eod-ecosystem --force
```

### Generate Report Only
```bash
tools.as run eod-ecosystem --report-only
```

### Skip Historical Storage
```bash
tools.as run eod-ecosystem --no-historical
```

## Scheduling

The command is pre-configured for:
- **Daily**: 6:00 PM - Standard ecosystem snapshot
- **Weekly**: Sunday 7:00 PM - Comprehensive analysis with force refresh

## Outputs

1. **Ecosystem Snapshots**: Stored in memOS.as semantic memory
2. **Daily Reports**: Generated as markdown files
3. **Health Metrics**: Exported to Prometheus (if available)
4. **Progress Logs**: Stored in memOS.as episodic memory

## Monitoring

The system monitors:
- Processing success rates across all projects
- Ecosystem health score trends
- Individual project status changes
- memOS storage success

## Dependencies

**Required Services:**
- InGest-LLM.as (ingestion service)
- memOS.as (knowledge storage)

**External Dependencies:**
- LM Studio (for embeddings)
- Langfuse (for observability)

**Optional:**
- Prometheus (metrics)
- Grafana (dashboards)

## Troubleshooting

### Common Issues

**Command not found:**
- Verify tools.as can find the command configuration
- Check file permissions and paths

**Service connectivity:**
- Ensure InGest-LLM.as is running on expected port
- Verify memOS.as connectivity

**Processing failures:**
- Check project directories exist and are accessible
- Verify sufficient disk space for processing
- Review logs for specific error details

### Recovery Steps

1. Check service status: `docker-compose ps`
2. Review logs: `docker-compose logs ingest-llm-as`
3. Test connectivity: `curl http://localhost:8000/health`
4. Force refresh: `tools.as run eod-ecosystem --force`

## Configuration Customization

Edit the TOML file to customize:
- Scheduling times
- Processing parameters  
- Output locations
- Monitoring thresholds
- Notification settings

## Integration with Existing Workflows

This ecosystem command integrates with:
- Daily development workflows
- CI/CD pipelines
- Team reporting systems
- Project health monitoring
- Knowledge management processes

For additional customization and advanced integration patterns, refer to the tools.as documentation and the ApexSigma ecosystem architecture guides.
"""

    return readme_content


if __name__ == "__main__":
    print("Generating tools.as integration configurations...")
    create_tools_as_integration_files()
    print("\n✅ Integration files generated successfully!")
    print("\nNext steps:")
    print("1. Copy the TOML file to your tools.as commands directory")
    print("2. Update tools.as configuration to include the new command")
    print("3. Test with: tools.as run eod-ecosystem --report-only")
