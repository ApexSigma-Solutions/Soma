#!/usr/bin/env python3
"""
Service Manager with Auto-Healing
Monitors and maintains all OmegaKG infrastructure services
"""

import asyncio
import time
from pathlib import Path
from typing import Dict, Tuple
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Reuse health check functions
from scripts.infrastructure.health_check import (
    check_postgres,
    check_redis,
    check_neo4j,
    check_ollama,
    check_ingest_llm,
)


class ServiceManager:
    """Manages and auto-heals infrastructure services"""

    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self.service_status: Dict[str, bool] = {}
        self.failure_counts: Dict[str, int] = {}

    async def check_all_services(self) -> Tuple[Dict[str, bool], int]:
        """Check all services and return status"""
        services = {
            "PostgreSQL": await check_postgres(),
            "Redis": await check_redis(),
            "Neo4j": check_neo4j(),
            "Ollama": await check_ollama(),
            "InGest-LLM": await check_ingest_llm(),
        }

        healthy = sum(services.values())
        return services, healthy

    async def heal_service(self, service_name: str):
        """Attempt to restart a failed service"""
        print(f"\n🔧 Attempting to heal {service_name}...")

        # Service-specific healing logic
        if service_name == "Redis":
            print("   Try: docker start memos-redis-mcp")
        elif service_name == "PostgreSQL":
            print("   Try: docker start apexsigma.postgres.stable")
        elif service_name == "Neo4j":
            print("   Try: docker start apexsigma.neo4j.stable")
        elif service_name == "Ollama":
            print("   Ollama runs natively, check Windows service")
        elif service_name == "InGest-LLM":
            print(
                "   Try: cd InGest-LLM.as && uvicorn ingest_llm_as.main:app --port 8766"
            )

    async def monitor_loop(self, duration: int = 300):
        """Monitor services for specified duration (seconds)"""
        print("\n" + "=" * 60)
        print("Service Monitor - Auto-Healing Enabled")
        print(f"Check interval: {self.check_interval}s | Duration: {duration}s")
        print("=" * 60 + "\n")

        start_time = time.time()
        check_count = 0

        while time.time() - start_time < duration:
            check_count += 1
            print(f"\n[Check #{check_count}] {time.strftime('%H:%M:%S')}")

            services, healthy = await self.check_all_services()
            self.service_status = services

            # Track failures
            for service, is_healthy in services.items():
                if not is_healthy:
                    self.failure_counts[service] = (
                        self.failure_counts.get(service, 0) + 1
                    )

                    # Auto-heal after 2 consecutive failures
                    if self.failure_counts[service] >= 2:
                        await self.heal_service(service)
                        self.failure_counts[service] = 0
                else:
                    self.failure_counts[service] = 0

            print(f"\nStatus: {healthy}/5 services healthy")

            if healthy == 5:
                print("✅ All systems operational")
            else:
                failed = [name for name, status in services.items() if not status]
                print(f"⚠️  Issues: {', '.join(failed)}")

            # Wait for next check
            await asyncio.sleep(self.check_interval)

        print("\n" + "=" * 60)
        print(f"Monitoring complete - {check_count} checks performed")
        print("=" * 60)

    async def run_once(self) -> bool:
        """Run single health check, return True if all healthy"""
        print("\n" + "=" * 60)
        print("Quick Health Check")
        print("=" * 60 + "\n")

        services, healthy = await self.check_all_services()

        print(f"\n{'=' * 60}")
        print(f"Result: {healthy}/5 services healthy")
        print("=" * 60)

        if healthy == 5:
            print("✅ All systems operational\n")
            return True
        else:
            failed = [name for name, status in services.items() if not status]
            print(f"⚠️  Issues: {', '.join(failed)}\n")
            return False


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Service Manager with Auto-Healing")
    parser.add_argument(
        "--monitor", action="store_true", help="Enable continuous monitoring"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=300,
        help="Monitor duration in seconds (default: 300)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Check interval in seconds (default: 30)",
    )

    args = parser.parse_args()

    manager = ServiceManager(check_interval=args.interval)

    if args.monitor:
        await manager.monitor_loop(duration=args.duration)
    else:
        all_healthy = await manager.run_once()
        sys.exit(0 if all_healthy else 1)


if __name__ == "__main__":
    asyncio.run(main())
