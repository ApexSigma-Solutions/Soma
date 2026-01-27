"""Percolator Client - The Courier.

Watches an Obsidian vault directory and ships file modifications
to the Soma.InGress service with debouncing to prevent flood.
"""

import os
import sys
import time
from threading import Timer
from typing import Dict

import requests
import structlog
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# --- Configuration ---
INGRESS_URL = os.getenv("SOMA_INGRESS_URL", "http://localhost:8000/api/v1/vault/sync")
API_KEY = os.getenv("SOMA_INGRESS_KEY", "sigma-dev-secret-key")
DEBOUNCE_SECONDS = float(os.getenv("PERCOLATOR_DEBOUNCE", "1.0"))

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger("Percolator")


class VaultCourier(FileSystemEventHandler):
    """File system event handler that ships vault changes to InGress."""

    def __init__(self) -> None:
        """Initialize the courier with timer tracking."""
        self.timers: Dict[str, Timer] = {}

    def on_modified(self, event) -> None:
        """Handle file modification events with debouncing.

        Args:
            event: File system event from watchdog
        """
        if event.is_directory:
            return
        if not event.src_path.endswith(".md"):
            return

        # Cancel existing timer for this file if present
        if event.src_path in self.timers:
            self.timers[event.src_path].cancel()

        # Schedule debounced delivery
        self.timers[event.src_path] = Timer(
            DEBOUNCE_SECONDS, self.ship, args=[event.src_path]
        )
        self.timers[event.src_path].start()

    def ship(self, path: str) -> None:
        """Ship file content to InGress service.

        Args:
            path: Absolute path to the modified file
        """
        if path in self.timers:
            del self.timers[path]

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            payload = {
                "source": "obsidian",
                "file_path": str(path),
                "filename": os.path.basename(path),
                "content": content,
            }

            response = requests.post(
                INGRESS_URL,
                json=payload,
                headers={"X-API-Key": API_KEY},
                timeout=10,
            )
            response.raise_for_status()

            log.info(
                "courier_delivered",
                file=os.path.basename(path),
                status=response.status_code,
            )
        except requests.RequestException as e:
            log.error("courier_network_fail", file=os.path.basename(path), error=str(e))
        except OSError as e:
            log.error("courier_file_fail", file=os.path.basename(path), error=str(e))


def main() -> None:
    """Main entry point for the Percolator client."""
    # Default to common Obsidian vault path on Windows
    default_path = r"C:\Users\Sean\Obsidian\Brain"
    path = sys.argv[1] if len(sys.argv) > 1 else default_path

    if not os.path.exists(path):
        log.error("vault_not_found", path=path)
        print(f"Error: Vault path does not exist: {path}")
        print(f"Usage: python {sys.argv[0]} <vault_path>")
        sys.exit(1)

    log.info("percolator_start", vault_path=path, debounce=DEBOUNCE_SECONDS)
    print(f"🧪 Percolator watching: {path}")

    observer = Observer()
    observer.schedule(VaultCourier(), path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("percolator_stop")
        observer.stop()

    observer.join()


if __name__ == "__main__":
    main()
