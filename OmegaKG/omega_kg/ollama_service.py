"""
Ollama Service Management

Handles starting, stopping, and health checking the Ollama service.
"""

import logging
import platform
import subprocess
import time

import requests

from omega_kg.settings import settings

logger = logging.getLogger(__name__)


def check_ollama_health(timeout: int = 5) -> bool:
    """
    Check if Ollama service is responding.

    Args:
        timeout: Request timeout in seconds

    Returns:
        True if Ollama is healthy, False otherwise
    """
    try:
        response = requests.get(f"{settings.ollama_host_url}/", timeout=timeout)
        return response.status_code == 200
    except Exception as e:
        logger.debug(f"Ollama health check failed: {e}")
        return False


def start_ollama_service() -> bool:
    """
    Start the Ollama service if it's not already running.

    Returns:
        True if Ollama is running after this call, False otherwise
    """
    # First check if already running
    if check_ollama_health(timeout=2):
        logger.info("✓ Ollama service already running")
        return True

    logger.info("Starting Ollama service...")

    try:
        if platform.system() == "Windows":
            # Try to start Ollama on Windows
            # Option 1: If installed as a service
            try:
                subprocess.run(
                    ["net", "start", "Ollama"], capture_output=True, check=False
                )
                time.sleep(2)  # Give service time to start
            except Exception:
                pass

            # Option 2: Start Ollama executable directly in background
            try:
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                time.sleep(3)  # Give it time to start
            except FileNotFoundError:
                logger.warning("Ollama executable not found in PATH")
                return False
        else:
            # Linux/Mac: try systemctl or direct command
            try:
                subprocess.run(["systemctl", "start", "ollama"], check=False)
                time.sleep(2)
            except FileNotFoundError:
                # Try starting directly
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                time.sleep(3)

        # Verify it started
        max_retries = 5
        for i in range(max_retries):
            if check_ollama_health():
                logger.info(
                    f"✓ Ollama service started successfully (took {i + 1} attempts)"
                )
                return True
            time.sleep(2)

        logger.error("Failed to start Ollama service after multiple attempts")
        return False

    except Exception as e:
        logger.error(f"Error starting Ollama service: {e}")
        return False


def ensure_ollama_running() -> bool:
    """
    Ensure Ollama is running, start it if needed.

    Returns:
        True if Ollama is running, False otherwise
    """
    if check_ollama_health():
        return True

    logger.info("Ollama not detected, attempting to start...")
    return start_ollama_service()


def get_ollama_status() -> dict:
    """
    Get detailed Ollama service status.

    Returns:
        Dictionary with status information
    """
    status = {"running": False, "url": settings.ollama_host_url, "models_loaded": []}

    try:
        # Check basic health
        if not check_ollama_health():
            return status

        status["running"] = True

        # Try to get loaded models
        try:
            response = requests.get(f"{settings.ollama_host_url}/api/ps", timeout=2)
            if response.status_code == 200:
                models = response.json().get("models", [])
                status["models_loaded"] = [m.get("name", "unknown") for m in models]
        except Exception as e:
            logger.debug(f"Could not get loaded models from Ollama: {e}")

    except Exception as e:
        logger.debug(f"Error getting Ollama status: {e}")

    return status
