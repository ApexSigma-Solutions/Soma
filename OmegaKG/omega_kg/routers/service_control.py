import logging
import subprocess
import os
import psutil
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Security
from pydantic import BaseModel

from omega_kg.auth_utils import validate_access_token

router = APIRouter(tags=["System Control"])
logger = logging.getLogger(__name__)


class ServiceAction(BaseModel):
    service_name: str
    action: str  # "start" | "stop" | "restart"


# Configuration for services
# Assuming relative paths from the Omega_KG_stable root where this server runs
BASE_DIR = Path.cwd().parent
# D:\projects\OmegaKG\Omega_KG_stable -> parent is D:\projects\OmegaKG

SERVICES_CONFIG = {
    "omega": {
        "name": "OmegaKG",
        "cwd": BASE_DIR / "Omega_KG_stable",
        "command": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\start_full_stack.ps1 -Persistent",
        "port": 8765,
    },
    "ingest": {
        "name": "InGest-LLM",
        "cwd": BASE_DIR / "InGest-LLM.as",
        "command": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\start_ingest_llm.ps1 -Persistent",
        "port": 8766,
    },
    "memos": {
        "name": "memOS.MCP",
        "cwd": BASE_DIR / "memos.MCP",
        "command": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\startup\\start-mcp.ps1 -Background",
        "port": 8768,
    },
}

# Keep track of subprocesses launched by this instance
_subprocess_registry: Dict[str, subprocess.Popen] = {}


def _kill_process_on_port(port: int):
    """
    Kill any process listening on the specified port.
    Uses psutil for cross-platform support.
    """
    try:
        for proc in psutil.process_iter(["pid", "name", "connections"]):
            try:
                for conn in proc.connections():
                    if conn.laddr.port == port:
                        logger.info(
                            f"Killing process {proc.pid} ({proc.name()}) on port {port}"
                        )
                        proc.terminate()
                        try:
                            proc.wait(timeout=3)
                        except psutil.TimeoutExpired:
                            proc.kill()
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception as e:
        logger.error(f"Error killing process on port {port}: {e}")
    return False


@router.post("/system/service")
async def control_service(
    data: ServiceAction, _token: Dict[str, Any] = Security(validate_access_token)
):
    """
    Start, stop, or restart a satellite service (InGest, Memos).
    """
    service_key = data.service_name.lower()
    action = data.action.lower()

    # Map common names
    if "ingest" in service_key:
        service_key = "ingest"
    elif "memos" in service_key:
        service_key = "memos"

    if service_key not in SERVICES_CONFIG:
        raise HTTPException(404, f"Service '{data.service_name}' not configured")

    config = SERVICES_CONFIG[service_key]

    if action == "stop":
        # 1. Check if we have a managed subprocess
        if service_key in _subprocess_registry:
            proc = _subprocess_registry[service_key]
            if proc.poll() is None:  # Running
                logger.info(f"Stopping managed {service_key} (PID {proc.pid})...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
            del _subprocess_registry[service_key]

        # 2. Force cleanup by port (catch manually started instances)
        _kill_process_on_port(config["port"])
        return {"status": "stopped", "service": config["name"]}

    elif action == "start":
        # Check if port is already in use
        if _is_port_in_use(config["port"]):
            return {
                "status": "already_running",
                "service": config["name"],
                "message": "Port in use",
            }

        try:
            cwd = config["cwd"]
            if not cwd.exists():
                raise HTTPException(500, f"Service directory not found: {cwd}")

            logger.info(f"Starting {config['name']} in {cwd}")

            # Use shell=True to pick up 'poetry' from PATH on Windows
            # redirect stdout/stderr to capture logs? For now, inherit or devnull
            # Using creationflags=subprocess.CREATE_NEW_CONSOLE might be annoying popup
            # subprocess.CREATE_NO_WINDOW is better.

            flags = 0
            if os.name == "nt":
                flags = subprocess.CREATE_NO_WINDOW

            proc = subprocess.Popen(
                config["command"], cwd=str(cwd), shell=True, creationflags=flags
            )

            _subprocess_registry[service_key] = proc
            return {"status": "started", "service": config["name"], "pid": proc.pid}

        except Exception as e:
            logger.error(f"Failed to start {service_key}: {e}", exc_info=True)
            raise HTTPException(500, f"Start failed: {str(e)}")

    elif action == "restart":
        # Stop first
        await control_service(
            ServiceAction(service_name=service_key, action="stop"), _token
        )
        # Then start
        return await control_service(
            ServiceAction(service_name=service_key, action="start"), _token
        )

    raise HTTPException(400, "Invalid action")


def _is_port_in_use(port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


@router.post("/system/ecosystem/shutdown")
async def shutdown_ecosystem(
    full: bool = False, _token: Dict[str, Any] = Security(validate_access_token)
) -> Dict[str, Any]:
    """
    Shut down the ecosystem. Defaults to stopping applications only.
    Use full=true via query parameter to stop Docker databases as well.
    """
    try:
        # Path to stop_ecosystem.ps1 (root of project)
        stop_script = BASE_DIR / "stop_ecosystem.ps1"
        if not stop_script.exists():
            raise HTTPException(500, f"Shutdown script not found at {stop_script}")

        mode = "Full" if full else "Apps-Only"
        logger.info(f"Initiating Ecosystem Shutdown ({mode}) via stop_ecosystem.ps1...")

        # We need to run this detached so the server can respond before it gets killed
        flags = 0
        if os.name == "nt":
            flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS

        # Construct arguments
        script_args = ["-AppsOnly"]
        if full:
            script_args = ["-Full"]

        subprocess.Popen(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(stop_script),
            ]
            + script_args,
            cwd=str(BASE_DIR),
            creationflags=flags,
            shell=True,
        )

        return {
            "status": "shutdown_initiated",
            "message": f"Ecosystem shutdown ({mode}) initiated",
        }
    except Exception as e:
        logger.error(f"Shutdown trigger failed: {e}")
        raise HTTPException(500, f"Shutdown trigger failed: {str(e)}")


@router.post("/system/ecosystem/restart")
async def restart_ecosystem(
    _token: Dict[str, Any] = Security(validate_access_token),
) -> Dict[str, Any]:
    """
    Restart the entire ecosystem.
    """
    try:
        # We'll use a wrapper command that stops then starts
        stop_script = BASE_DIR / "stop_ecosystem.ps1"
        launch_script = (
            BASE_DIR / "start_ecosystem.ps1"
        )  # We use start_ecosystem directly with persistence

        if not stop_script.exists() or not launch_script.exists():
            raise HTTPException(500, "Required scripts (stop/start) not found")

        logger.info("Initiating Ecosystem Restart...")

        # Create a transient batch file or sequential command
        restart_cmd = f'powershell -NoProfile -ExecutionPolicy Bypass -File "{stop_script}" -AppsOnly; Start-Sleep -Seconds 5; powershell -NoProfile -ExecutionPolicy Bypass -File "{launch_script}" -Persistent'

        flags = 0
        if os.name == "nt":
            flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS

        subprocess.Popen(
            restart_cmd, cwd=str(BASE_DIR), creationflags=flags, shell=True
        )

        return {"status": "restart_initiated", "message": "Ecosystem is restarting"}
    except Exception as e:
        logger.error(f"Restart trigger failed: {e}")
        raise HTTPException(500, f"Restart trigger failed: {str(e)}")
