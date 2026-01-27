import asyncio
import logging

# --- LOGGING SETUP ---
import os
import time
from datetime import datetime, timezone

import requests

from omega_kg.database.quipu import init_heartbeat_table, insert_heartbeat
from omega_kg.settings import settings

log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level.upper(), logging.INFO),
    format="%(asctime)s - [QUIPU] - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("QuipuMonitor")


def check_ollama_health():
    """
    Pings the Ollama instance to check liveness and loaded models.
    Returns: (status_str, latency_int, active_model_str, meta_dict)
    """
    ollama_url = settings.ollama_host_url
    start_time = time.time()
    try:
        # 1. Basic Liveness (GET /)
        resp = requests.get(f"{ollama_url}/", timeout=5)
        resp.raise_for_status()

        # 2. Check for loaded models (GET /api/ps)
        model_name = "None"
        try:
            ps_resp = requests.get(f"{ollama_url}/api/ps", timeout=2)
            if ps_resp.status_code == 200:
                models = ps_resp.json().get("models", [])
                if models:
                    model_name = models[0].get("name", "Unknown")
        except Exception:
            pass  # Non-critical failure for model check

        latency = int((time.time() - start_time) * 1000)
        return "ONLINE", latency, model_name, {"url": ollama_url}

    except requests.exceptions.ConnectionError:
        logger.warning(f"Ollama Unreachable at {ollama_url}")
        return "OFFLINE", 0, None, {"error": "Connection Refused"}
    except requests.exceptions.Timeout:
        logger.warning(f"Ollama Timeout at {ollama_url}")
        return "TIMEOUT", 5000, None, {"error": "Request Timed Out"}
    except Exception as e:
        logger.error(f"Ollama Check Failed: {e}")
        return "ERROR", 0, None, {"error": str(e)}


async def run_heartbeat_loop():
    """Main Service Loop"""
    logger.info("Starting Quipu Heartbeat Monitor...")

    if not await init_heartbeat_table():
        logger.critical("Could not initialize Database. Service aborting.")
        return

    logger.info(
        f"Target: {settings.ollama_host_url} | Interval: {settings.heartbeat_interval_sec}s"
    )

    while True:
        try:
            timestamp = datetime.now(timezone.utc)
            status, latency, model, meta = check_ollama_health()

            success = await insert_heartbeat(
                service_name=settings.quipu_service_name,
                timestamp=timestamp,
                status=status,
                latency_ms=latency,
                model_loaded=model,
                meta=meta,
            )

            if success:
                if status != "ONLINE":
                    logger.warning(f"Status: {status} | Latency: {latency}ms")
                else:
                    logger.debug(f"Tick: {status} | {latency}ms")
            else:
                logger.error("DB Write Failed for this tick.")

            time.sleep(settings.heartbeat_interval_sec)

        except KeyboardInterrupt:
            logger.info("Stopping Heartbeat Monitor...")
            break
        except Exception as main_e:
            logger.error(f"Critical Loop Error: {main_e}")
            time.sleep(5)  # Prevent tight loop on crash


if __name__ == "__main__":
    asyncio.run(run_heartbeat_loop())
