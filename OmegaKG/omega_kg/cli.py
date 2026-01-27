"""
Omega_KG Command Line Interface
Unified entry point for all operations
"""

import click

from omega_kg.lifecycle import TaskLifecycle
from omega_kg.neo4j_schema import KnowledgeGraphSchema


@click.group()
def cli():
    """
    Omega_KG: Neo4j-powered knowledge management with Obsidian sync and task lifecycle enforcement.

    Available commands:
    - init: Initialize Neo4j schema
    - sync: Sync Obsidian vault to Neo4j
    - lifecycle: Enforce task lifecycle rules
    - status: Check connection status
    - report: Generate lifecycle report
    - stats: Show task statistics
    - stale: List stale tasks
    """
    pass


@cli.command()
def init():
    """
    Initialize the Neo4j schema and populate example relationships.

    Sets up the required schema (nodes, constraints) and creates sample relationships for demonstration. Ensures the schema connection is closed when finished.
    """
    click.echo("🔧 Initializing Neo4j schema...")
    schema = KnowledgeGraphSchema()
    schema.initialize_schema()
    schema.create_sample_relationships()
    schema.close()
    click.echo("✓ Schema initialized")


@cli.command()
@click.option("--dry-run", is_flag=True, help="Preview changes")
@click.option("--no-email", is_flag=True, help="Skip email report")
def lifecycle(dry_run, no_email):
    """
    Run task lifecycle enforcement, print a human-readable report, and optionally send it by email.

    Parameters:
        dry_run (bool): Simulate lifecycle changes without applying them.
        no_email (bool): Do not send the generated email report.
    """
    lc = TaskLifecycle()

    try:
        click.echo("🔄 Running lifecycle enforcement...")
        results = lc.enforce_lifecycle(dry_run=dry_run)

        report = lc.generate_report(results)
        click.echo(f"\n{report}")

        if not dry_run and not no_email:
            lc.send_email_report(report)

    finally:
        lc.close()


@cli.command()
def stats():
    """
    Show aggregated counts of Task nodes in the knowledge graph and print them to the console.

    Connects to the configured Neo4j instance (or uses mock mode if no connection) and prints counts for total, draft, active, completed, and archived tasks. Ensures opened sync client and database driver are closed before returning.
    """
    from omega_kg.obsidian_sync import ObsidianNeo4jSync

    click.echo("\n✓ Neo4j connection established\n")
    click.echo("📊 Knowledge Graph Statistics")
    click.echo("━" * 35)

    sync = ObsidianNeo4jSync()
    status = sync.get_connection_status()

    if not status["connected"]:
        click.echo("[WARN] Running in mock mode (no connection)")
        sync.close()
        return

    try:
        from neo4j import GraphDatabase
        from omega_kg.settings import settings

        driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )

        with driver.session() as session:
            result = session.run(
                """
                MATCH (t:Task)
                RETURN count(t) as total,
                       count(CASE WHEN t.status = 'draft'
                             THEN 1 END) as draft,
                       count(CASE WHEN t.status = 'active'
                             THEN 1 END) as active,
                       count(CASE WHEN t.status = 'completed'
                             THEN 1 END) as completed,
                       count(CASE WHEN t.status = 'archived'
                             THEN 1 END) as archived
            """
            )
            record = result.single()

        driver.close()

        if record:
            click.echo(f"Total Tasks:      {record['total']}")
            click.echo(f"Draft:            {record['draft']}")
            click.echo(f"Active:           {record['active']}")
            click.echo(f"Completed:        {record['completed']}")
            click.echo(f"Archived:         {record['archived']}")
        else:
            click.echo("No tasks found")

    finally:
        sync.close()


@cli.command()
def stale():
    """
    Print tasks older than 7 days to the console, showing each task's UID, title, and creation date.

    If stale tasks exist, prints a header and one line per task in the format "uid: title (created: date)". If no stale tasks are found, prints "(none)". The function closes the sync client before returning.
    """
    from omega_kg.obsidian_sync import ObsidianNeo4jSync

    sync = ObsidianNeo4jSync()
    stale = sync.get_stale_tasks(7)

    if stale:
        click.echo("\n--- Stale Tasks (>7 days) ---")
        for task in stale:
            click.echo(
                f"{task['t.uid']}: {task['t.title']} (created: {task['t.created']})"
            )
    else:
        click.echo("(none)")

    sync.close()


@cli.command()
@click.option("--mock", is_flag=True, help="Run in mock mode (no database)")
def sync(mock):
    """
    Synchronize all task notes from Obsidian vault to Neo4j.

    Scans the vault's Tasks directory and creates/updates Task nodes in Neo4j
    with metadata from frontmatter and content. Supports mock mode for testing.
    """
    from omega_kg.obsidian_sync import ObsidianNeo4jSync

    click.echo("🔄 Syncing Obsidian vault to Neo4j...")

    syncer = ObsidianNeo4jSync(mock_mode=mock)

    try:
        status = syncer.get_connection_status()
        if status["connected"]:
            click.echo(f"✓ Connected to Neo4j: {status['uri']}")
        else:
            click.echo("⚠ Running in mock mode (no Neo4j connection)")

        count = syncer.sync_all_tasks()
        click.echo(f"\n✓ Synced {count} tasks")

    finally:
        syncer.close()


@cli.command()
def status():
    """
    Check and display connection status for Neo4j and system components.

    Reports on database connectivity, configuration, and system health.
    """
    from omega_kg.lifecycle import TaskLifecycle
    from omega_kg.settings import settings

    click.echo("🔍 System Status Check")
    click.echo("=" * 50)

    # Check lifecycle connection
    lc = TaskLifecycle()
    lc_status = lc.get_connection_status()

    click.echo("\n📊 Neo4j Connection:")
    click.echo(f"  URI:         {lc_status['uri']}")
    click.echo(f"  Connected:   {'✓ Yes' if lc_status['connected'] else '✗ No'}")
    click.echo(f"  Mock Mode:   {'Yes' if lc_status['mock_mode'] else 'No'}")

    click.echo("\n📁 Configuration:")
    click.echo(f"  Environment: {settings.app_env}")
    click.echo(f"  Vault Path:  {settings.obsidian_vault_path}")

    click.echo("\n📧 Email Settings:")
    if settings.smtp_host and settings.smtp_user and settings.email_to:
        click.echo(f"  SMTP Host:   {settings.smtp_host}:{settings.smtp_port}")
        click.echo(f"  From:        {settings.smtp_user}")
        click.echo(f"  To:          {settings.email_to}")
        click.echo("  Status:      ✓ Configured")
    else:
        click.echo("  Status:      ✗ Not configured")

    click.echo("\n🔗 Linear Integration:")
    if settings.linear_api_key:
        click.echo("  API Key:     ✓ Configured")
        click.echo(f"  Team ID:     {settings.linear_team_id or 'Not set'}")
    else:
        click.echo("  Status:      ✗ Not configured")

    lc.close()


@cli.command()
@click.option("--email", is_flag=True, help="Send report via email")
def report(email):
    """
    Generate and display a lifecycle report with task statistics and actions.

    Shows auto-archived tasks, warnings, stale active tasks, and summary counts.
    Can optionally send the report via email. This command does not apply any
    lifecycle changes - it only reports on current state.
    """
    lc = TaskLifecycle()

    try:
        click.echo("📊 Generating lifecycle report...")

        status = lc.get_connection_status()
        if status["connected"]:
            click.echo(f"✓ Connected to Neo4j: {status['uri']}")
        else:
            click.echo("⚠ Running in mock mode (generating sample report)")

        # Run enforcement in dry-run mode to get current state without changes
        results = lc.enforce_lifecycle(dry_run=True)

        # Generate report
        report_text = lc.generate_report(results)
        click.echo(f"\n{report_text}")

        if email:
            lc.send_email_report(report_text)

    finally:
        lc.close()


if __name__ == "__main__":
    cli()
