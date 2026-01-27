import asyncio
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from rich.console import Console
from rich.panel import Panel
from watchfiles import awatch

# Configuration
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

LOG_DIR = Path("d:/projects/OmegaKG/logs")
REPORT_DIR = LOG_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

console = Console()


class LogAggregator:
    def __init__(self):
        self.errors: List[Dict] = []
        self.anomalies: List[Dict] = []
        self.stats = defaultdict(int)
        self.processed_positions: Dict[str, int] = {}
        self.start_time = datetime.now()

    def process_line(self, line: str, service: str):
        try:
            record = json.loads(line)
            level = record.get("level", "info").lower()

            self.stats[f"{service}_{level}"] += 1

            if level in ["error", "critical", "fatal"]:
                record["service"] = service
                self.errors.append(record)
            elif level == "warning":
                record["service"] = service
                self.anomalies.append(record)

        except json.JSONDecodeError:
            pass

    async def generate_report(self):
        timestamp = datetime.now().strftime("%Y-%m-%d")
        report_file = REPORT_DIR / f"Daily_Log_Summary_{timestamp}.md"

        unique_errors = self._deduplicate_events(self.errors)
        unique_anomalies = self._deduplicate_events(self.anomalies)

        content = f"# Daily Log Summary - {timestamp}\n\n"
        content += f"**Generated At:** {datetime.now().isoformat()}\n"
        content += f"**Monitoring Started:** {self.start_time.isoformat()}\n\n"

        content += "## 📊 Statistics\n\n"
        content += "| Service | Level | Count |\n"
        content += "|---|---|---|\n"
        for key, count in sorted(self.stats.items()):
            service, level = key.rsplit("_", 1)
            content += f"| {service} | {level.upper()} | {count} |\n"

        content += "\n## 🚨 Critical Errors & Anomalies\n\n"

        if not unique_errors:
            content += "✅ No critical errors detected.\n"
        else:
            for error in unique_errors:
                content += (
                    f"### [{error['service']}] {error.get('event', 'Unknown Error')}\n"
                )
                content += f"- **Timestamp:** {error.get('timestamp')}\n"
                content += f"- **Count:** {error['count']}\n"
                if "exception" in error:
                    content += f"- **Exception:** `{error['exception']}`\n"
                content += "\n"

        content += "\n## ⚠️ Warnings\n\n"
        if not unique_anomalies:
            content += "✅ No warnings detected.\n"
        else:
            for anomaly in unique_anomalies:
                content += f"- **[{anomaly['service']}]** {anomaly.get('event', 'Unknown Warning')} (x{anomaly['count']})\n"

        content += "\n## 🛠️ Suggested Actions (Issues to Create)\n\n"
        if unique_errors:
            for idx, error in enumerate(unique_errors, 1):
                content += f"{idx}. **Fix {error['service']} Error:** {error.get('event', 'Unknown Error')}\n"
                content += "   - Priority: High\n"
                content += f"   - Description: Investigate repeated error in {error['service']} logs.\n"
        else:
            content += "No immediate actions required.\n"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(content)

        console.print(f"[green]Report generated: {report_file}[/green]")

    def _deduplicate_events(self, events: List[Dict]) -> List[Dict]:
        """Aggregate events by service + event message."""
        deduped = {}
        for event in events:
            key = f"{event['service']}:{event.get('event', '')}"
            if key not in deduped:
                event["count"] = 1
                deduped[key] = event
            else:
                deduped[key]["count"] += 1
        return list(deduped.values())


async def watch_logs(run_once: bool = False):
    aggregator = LogAggregator()
    console.print(
        Panel.fit(
            "Starting Log Watchdog...", title="OmegaKG Watchdog", border_style="blue"
        )
    )

    # Initial scan
    for log_file in LOG_DIR.glob("*.json.log"):
        service = log_file.name.replace(".json.log", "")
        if log_file.exists():
            # Only read new lines in future? Or read entire file for "Day"?
            # Let's read the whole file for the day context.
            async with asyncio.Lock():
                with open(log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    aggregator.processed_positions[str(log_file)] = f.tell()
                    for line in lines:
                        aggregator.process_line(line, service)

    await aggregator.generate_report()

    if run_once:
        console.print("[blue]Run once completed. Exiting.[/blue]")
        return

    async for changes in awatch(LOG_DIR):
        for change_type, path in changes:
            path_obj = Path(path)
            if path_obj.match("*.json.log"):
                service = path_obj.name.replace(".json.log", "")

                # Read new lines
                current_pos = aggregator.processed_positions.get(path, 0)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        f.seek(current_pos)
                        new_lines = f.readlines()
                        aggregator.processed_positions[path] = f.tell()

                        if new_lines:
                            console.print(
                                f"[dim]Processing {len(new_lines)} lines from {service}...[/dim]"
                            )
                            for line in new_lines:
                                aggregator.process_line(line, service)

                            # Simple logic: Generate report on every update?
                            # Or just keep aggregating.
                            # User said "generate a daily log summary report".
                            # Let's generate it periodically or on exit.
                            # But to see immediate results, we can update it.
                            await aggregator.generate_report()

                except Exception as e:
                    console.print(f"[red]Error reading {path}: {e}[/red]")


if __name__ == "__main__":
    try:
        run_once = "--once" in sys.argv
        asyncio.run(watch_logs(run_once=run_once))
    except KeyboardInterrupt:
        console.print("[yellow]Watchdog stopped.[/yellow]")
