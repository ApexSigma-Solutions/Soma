import re
import logging
from pathlib import Path
from fastapi import APIRouter, Security
from omega_kg.routers.auth import validate_access_token
from omega_kg.models.log_summary import (
    LogSummaryResponse,
    LogSummaryReport,
    LogSummaryStats,
    CriticalError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system/logs", tags=["system"])


def parse_summary_md(content: str) -> LogSummaryReport:
    """Parses the generated Markdown log summary into a structured report."""

    # Extract metadata from top
    date_match = re.search(r"# Daily Log Summary - (\d{4}-\d{2}-\d{2})", content)
    gen_match = re.search(r"\*\*Generated At:\*\* ([\d\-T:\.]+)", content)
    mon_match = re.search(r"\*\*Monitoring Started:\*\* ([\d\-T:\.]+)", content)

    report = LogSummaryReport(
        date=date_match.group(1) if date_match else "Unknown",
        generated_at=gen_match.group(1) if gen_match else "Unknown",
        monitoring_started=mon_match.group(1) if mon_match else "Unknown",
    )

    # Split into sections by "## "
    sections = re.split(r"\n## ", content)

    for section in sections:
        # Statistics
        if "📊 Statistics" in section:
            rows = re.findall(r"\| (.*?) \| (.*?) \| (\d+) \|", section)
            for service, level, count in rows:
                if service != "Service":  # Skip header
                    report.stats.append(
                        LogSummaryStats(
                            service=service.strip(),
                            level=level.strip(),
                            count=int(count),
                        )
                    )

        # Critical Errors
        elif "🚨 Critical Errors & Anomalies" in section:
            # Sub-headers look like ### [Service] Title
            # Use finditer to get ranges for body extraction
            header_pattern = r"### \[(.*?)\] (.*?)\s*\n"
            matches = list(re.finditer(header_pattern, section))
            for idx, match in enumerate(matches):
                service = match.group(1)
                title = match.group(2)
                start_pos = match.end()
                end_pos = (
                    matches[idx + 1].start() if idx + 1 < len(matches) else len(section)
                )
                body = section[start_pos:end_pos]

                ts_match = re.search(r"- \*\*Timestamp:\*\* (.*?)\n", body)
                count_match = re.search(r"- \*\*Count:\*\* (\d+)", body)

                report.critical_errors.append(
                    CriticalError(
                        service=service.strip(),
                        message=title.strip(),
                        timestamp=ts_match.group(1).strip() if ts_match else "Unknown",
                        count=int(count_match.group(1)) if count_match else 1,
                    )
                )

        # Warnings
        elif "⚠️ Warnings" in section:
            lines = section.strip().split("\n")[1:]  # Skip title
            report.warnings = [
                line.strip("- ").strip() for line in lines if line.strip()
            ]

        # Suggested Actions
        elif "🛠️ Suggested Actions" in section:
            lines = section.strip().split("\n")[1:]  # Skip title
            current_action = ""
            for line in lines:
                clean_line = line.strip()
                if not clean_line:
                    continue
                if re.match(r"^\d+\.", clean_line):
                    if current_action:
                        report.suggested_actions.append(current_action)
                    current_action = clean_line
                elif current_action:
                    current_action += " " + clean_line
            if current_action:
                report.suggested_actions.append(current_action)

    return report


@router.get("/summary", response_model=LogSummaryResponse)
async def get_latest_log_summary(
    _token_payload: dict = Security(validate_access_token),
):
    """Fetches the latest generated log summary markdown and returns it as structured JSON."""
    try:
        reports_dir = Path("d:/projects/OmegaKG/logs/reports")
        if not reports_dir.exists():
            return LogSummaryResponse(
                status="error", message="Reports directory not found"
            )

        # Find latest file
        files = sorted(reports_dir.glob("Daily_Log_Summary_*.md"), reverse=True)
        if not files:
            return LogSummaryResponse(status="error", message="No log summaries found")

        latest_file = files[0]
        content = latest_file.read_text(encoding="utf-8")

        report = parse_summary_md(content)

        return LogSummaryResponse(status="success", report=report)

    except Exception as e:
        logger.error(f"Error fetching log summary: {e}", exc_info=True)
        return LogSummaryResponse(status="error", message=f"Internal error: {str(e)}")
