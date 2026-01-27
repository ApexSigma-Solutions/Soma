"""Soma Ecosystem Orchestrator v2.9.

Python-based service launcher with Cloudflare Tunnel support.
Uses Windows Terminal for clean multi-tab service management.
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict

import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger("Orchestrator")

# Service definitions following biological naming
SERVICES: Dict[str, Dict[str, Any]] = {
    "Tunnel": {
        "script": "tunnel run",
        "cwd": ".",
        "icon": "🚇",
        "port": None,
        "description": "Cloudflare Tunnel - Public Ingress",
        "type": "binary",
        "bin": "cloudflared",
    },
    "InGress": {
        "script": "main.py",
        "cwd": "./InGress/soma_ingress",
        "icon": "👂",
        "port": 8000,
        "description": "The Senses - Data Capture Gateway",
        "type": "python",
    },
    "Stomach": {
        "script": "raw_lake_poller.py",
        "cwd": "./InGress/soma_ingress",
        "icon": "🫃",
        "port": None,
        "description": "The Stomach - Raw Lake Digestion Poller",
        "type": "python",
    },
    "OmegaKG": {
        "script": "main.py",
        "cwd": "./OmegaKG/omega_kg",
        "icon": "🧠",
        "port": 8765,
        "description": "The Brain - Knowledge Graph & Governance",
        "type": "python",
    },
    "memOS": {
        "script": "server.py",
        "cwd": "./memOS/src/memos_mcp",
        "icon": "✋",
        "port": 8768,
        "description": "The Hands - Context Bridge & Retrieval",
        "type": "python",
    },
}


class Orchestrator:
    """Service orchestrator using Windows Terminal for process management."""

    def __init__(self) -> None:
        """Initialize orchestrator with Windows Terminal path."""
        self.wt = "wt.exe"
        self.base_path = Path(__file__).parent.resolve()

    def launch(self, name: str) -> bool:
        """Launch a single service in a new Windows Terminal tab.

        Args:
            name: Name of the service to launch (must be in SERVICES dict)

        Returns:
            True if launch command was issued, False if service not found
        """
        cfg = SERVICES.get(name)
        if not cfg:
            logger.error("service_not_found", service=name)
            return False

        cwd = (self.base_path / cfg["cwd"]).resolve()

        # Build command based on service type
        if cfg.get("type") == "binary":
            # Direct binary execution (e.g., cloudflared)
            cmd_inner = f"{cfg['bin']} {cfg['script']}"
        else:
            # Python script execution
            if not cwd.exists():
                logger.error("cwd_not_found", service=name, path=str(cwd))
                return False
            cmd_inner = f"python {cfg['script']}"

        # Strategy: CMD /C START (Fixes PowerShell quoting issues)
        cmd = (
            f'cmd /c start "Orchestrator" {self.wt} -w 0 new-tab '
            f'--title "{cfg["icon"]} {name}" -d "{cwd}" '
            f'--profile "PowerShell" pwsh -NoExit -Command "{cmd_inner}"'
        )

        logger.info(
            "launching",
            service=name,
            port=cfg.get("port"),
            description=cfg["description"],
        )

        try:
            subprocess.run(cmd, shell=True, check=False)
            return True
        except Exception as e:
            logger.error("launch_failed", service=name, error=str(e))
            return False

    def launch_all(self, delay: float = 2.0) -> None:
        """Launch all services with a delay between each.

        Args:
            delay: Seconds to wait between launching services
        """
        # Launch order: Tunnel first, then Senses, then Stomach, then Brain
        launch_order = ["Tunnel", "InGress", "Stomach", "OmegaKG", "memOS"]
        logger.info("ecosystem_startup", version="2.9", services=launch_order)

        for service_name in launch_order:
            if service_name in SERVICES:
                self.launch(service_name)
                time.sleep(delay)

        logger.info("ecosystem_launched")

    def status(self) -> None:
        """Print status of all configured services."""
        print("\n" + "=" * 65)
        print("Soma Ecosystem Services (v2.9)")
        print("=" * 65)
        for name, cfg in SERVICES.items():
            port_str = f"Port {cfg['port']}" if cfg.get("port") else "No Port"
            print(f"{cfg['icon']} {name:12} | {port_str:10} | {cfg['description']}")
        print("=" * 65 + "\n")


def main() -> None:
    """Main entry point for orchestrator CLI."""
    app = Orchestrator()

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--status":
            app.status()
        elif arg in SERVICES:
            app.launch(arg)
        else:
            print(f"Unknown service: {arg}")
            print(f"Available: {', '.join(SERVICES.keys())}")
            sys.exit(1)
    else:
        app.status()
        app.launch_all()


if __name__ == "__main__":
    main()
