# omega_kg/ngrok_tunnel.py
"""
Ngrok Tunnel Integration for Linear Webhooks
"""

import logging
from typing import Optional
from pyngrok import ngrok, conf
from omega_kg.settings import settings  # Import the settings we fixed

logger = logging.getLogger(__name__)


class NgrokTunnel:
    """Manages Ngrok tunnel for webhook exposure"""

    def __init__(self):
        self.tunnel_url: Optional[str] = None
        self.auth_token: Optional[str] = None

    def is_enabled(self) -> bool:
        """Check if ngrok integration is enabled via Settings"""
        return settings.enable_ngrok

    async def start_tunnel(self, port: int = 8765):
        """Start ngrok tunnel programmatically"""
        if not self.is_enabled():
            logger.info("Ngrok tunnel disabled in settings.")
            return

        try:
            # 1. Get auth token from Pydantic Settings (Robust)
            self.auth_token = settings.ngrok_api_key

            if not self.auth_token:
                logger.warning(
                    "⚠️ ENABLE_NGROK is true, but NGROK_API_KEY is missing in settings!"
                )
                return None

            # 2. Force Authentication (The Critical Fix)
            # This overrides any local 'zombie' config files
            ngrok.set_auth_token(self.auth_token)

            # 3. Configure & Connect
            # We explicitly create a config to ensure clean startup
            pyngrok_config = conf.PyngrokConfig(auth_token=self.auth_token, region="us")

            tunnel = ngrok.connect(port, "http", pyngrok_config=pyngrok_config)
            self.tunnel_url = tunnel.public_url

            logger.info(f"🚀 Ngrok tunnel started: {self.tunnel_url}")
            logger.info(f"📡 Linear webhook URL: {self.tunnel_url}/webhook/linear")

            return self.tunnel_url

        except ImportError:
            logger.error(
                "pyngrok not installed. Install with: pip install pyngrok\n"
                "Also install ngrok CLI: https://ngrok.com/download"
            )
        except Exception as e:
            logger.error(f"Failed to start ngrok tunnel: {e}")

    async def stop_tunnel(self):
        """Stop ngrok tunnel"""
        if self.tunnel_url:
            try:
                ngrok.kill()
                logger.info("🛑 Ngrok tunnel stopped")
            except Exception as e:
                logger.error(f"Error stopping tunnel: {e}")


# Global tunnel instance (Critical for capture_server.py compatibility)
ngrok_tunnel = NgrokTunnel()
