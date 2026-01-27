import psutil
import shutil
import logging

# Try importing Nvidia lib, fail gracefully if on non-GPU machine
try:
    import pynvml

    HAS_GPU = True
except ImportError:
    HAS_GPU = False

logger = logging.getLogger(__name__)


class SystemHealth:
    """
    Somatic Nervous System.
    Checks physical hardware constraints.
    """

    @staticmethod
    def check_vitals() -> dict:
        vitals = {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "ram_percent": psutil.virtual_memory().percent,
            "disk_free_gb": round(shutil.disk_usage("/").free / (1024**3), 2),
            "gpu": SystemHealth._get_gpu_stats() if HAS_GPU else "No GPU Driver",
        }

        # Add vram_percent for dashboard compatibility
        if HAS_GPU and isinstance(vitals["gpu"], dict):
            used = vitals["gpu"].get("vram_used_mb", 0)
            total = vitals["gpu"].get("vram_total_mb", 1)  # Avoid div by zero
            vitals["vram_percent"] = round((used / total) * 100, 2)
        else:
            vitals["vram_percent"] = 0

        return vitals

    @staticmethod
    def is_healthy(ram_threshold=90.0) -> bool:
        """Simple boolean check for 'Can I eat this?'"""
        vitals = SystemHealth.check_vitals()
        if vitals["ram_percent"] > ram_threshold:
            logger.warning(f"System Stressed: RAM at {vitals['ram_percent']}%")
            return False
        return True

    @staticmethod
    def _get_gpu_stats():
        try:
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            return {
                "vram_used_mb": round(mem_info.used / 1024**2, 2),
                "vram_total_mb": round(mem_info.total / 1024**2, 2),
            }
        except Exception:
            return "GPU Detection Failed"
        finally:
            try:
                pynvml.nvmlShutdown()
            except:
                pass
