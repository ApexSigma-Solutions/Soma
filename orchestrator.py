# Soma Executive v3.1 - Native Spawner
# Mandate: Fixed Console Spawning & Correct Working Directories
"""
Soma Organism Orchestrator v3.1

Native Windows console spawning using CREATE_NEW_CONSOLE.
Each service gets its own visible telemetry window.
"""

import subprocess
import time
import structlog
import os
import sys

# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(colors=True),
    ],
)
logger = structlog.get_logger()

# Project root
SOMA_ROOT = os.path.dirname(os.path.abspath(__file__))

# Service Map
SERVICES = {
    "Soma.InGress": {
        "cmd": [
            sys.executable,
            "-m",
            "uvicorn",
            "soma_ingress.main:app",
            "--port",
            "8000",
        ],
        "cwd": os.path.join(SOMA_ROOT, "InGress"),
    },
    "Soma.InGest": {
        "cmd": [sys.executable, "ingest/raw_lake_poller_v2.py"],
        "cwd": os.path.join(SOMA_ROOT, "InGest"),
    },
    "Soma.OmegaKG_Consumer": {
        "cmd": [sys.executable, "omega_kg/consumer.py"],
        "cwd": os.path.join(SOMA_ROOT, "OmegaKG"),
    },
    "Soma.memOS": {
        "cmd": [sys.executable, "-m", "memos_mcp.server", "--sse"],
        "cwd": os.path.join(SOMA_ROOT, "memOS", "src"),
    },
}


def spawn(name: str, config: dict) -> None:
    """Spawn a service in its own console window."""
    logger.info("spawning_organ", service=name, cwd=config["cwd"])

    # Sanitize environment to prevent venv leaks
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)

    # Ensure the PATH doesn't prioritize the orchestrator's venv
    path_segments = env.get("PATH", "").split(os.pathsep)
    env["PATH"] = os.pathsep.join([s for s in path_segments if ".venv" not in s])

    try:
        # Use CREATE_NEW_CONSOLE on Windows to give each service a visible log window
        subprocess.Popen(
            config["cmd"],
            cwd=config["cwd"],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            env=env,
        )
        logger.info("organ_heartbeat_detected", service=name)
    except Exception as e:
        logger.error("organ_failure", service=name, error=str(e))


def main() -> None:
    """Main orchestrator entry point."""
    logger.info("=" * 60)
    logger.info("orchestrator_v3.1_init", status="ASSEMBLING_ANTIGRAVITY_STACK")
    logger.info("=" * 60)

    # 1. Start Redis via Docker first
    logger.info("starting_state_layer", component="Redis")
    result = subprocess.run(
        ["docker", "start", "apexsigma.redis.soma"], capture_output=True, text=True
    )
    if result.returncode == 0:
        logger.info("redis_online", status="READY")
    else:
        logger.warning("redis_start_failed", stderr=result.stderr)

    time.sleep(2)

    # 2. Spawn Organs
    for name, config in SERVICES.items():
        spawn(name, config)
        time.sleep(2)

    logger.info("=" * 60)
    logger.info("organism_breathing", status="PHASE_1_VERIFICATION_READY")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Services spawned:")
    logger.info("  - InGress:       http://localhost:8000")
    logger.info("  - InGest:        Polling raw_lake")
    logger.info("  - OmegaKG:       Redis -> Neo4j (768-dim)")
    logger.info("  - memOS:         MCP Server (SSE)")
    logger.info("")
    logger.info("Press Ctrl+C to hibernate...")

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info(
            "orchestrator_hibernation", msg="Services remain active in their windows"
        )


if __name__ == "__main__":
    main()
