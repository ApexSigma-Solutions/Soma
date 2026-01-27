#!/usr/bin/env python3
"""
Core Integration Test Runner for InGest-LLM.as → memOS.as

This script runs the core integration test suite that validates the workflow
between InGest-LLM.as and memOS.as services. It fulfills the P1-CC-02 requirement.
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict
import httpx

# Service Configuration
INGEST_SERVICE_URL = "http://localhost:8000"
MEMOS_SERVICE_URL = "http://localhost:8091"


class CoreIntegrationTestRunner:
    """Runner for core integration tests."""

    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir.parent
        self.test_file = self.project_root / "tests" / "test_memos_integration_core.py"

    async def check_service_health(self, url: str, service_name: str) -> Dict:
        """Check if a service is healthy."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{url}/health")

                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "service": service_name,
                        "data": response.json(),
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "service": service_name,
                        "code": response.status_code,
                    }

        except Exception as e:
            return {"status": "unreachable", "service": service_name, "error": str(e)}

    async def validate_services(self) -> bool:
        """Validate that required services are available."""
        print("🔍 Validating ApexSigma service ecosystem...")
        print("=" * 50)

        services = [
            (INGEST_SERVICE_URL, "InGest-LLM.as"),
            (MEMOS_SERVICE_URL, "memOS.as"),
        ]

        all_healthy = True

        for url, service_name in services:
            health_info = await self.check_service_health(url, service_name)

            status = health_info["status"]
            if status == "healthy":
                print(f"✅ {service_name:15} : {status:10} - {url}")
            elif status == "unhealthy":
                print(f"⚠️  {service_name:15} : {status:10} - {url}")
                all_healthy = False
            else:
                print(f"❌ {service_name:15} : {status:10} - {url}")
                all_healthy = False

        print("=" * 50)
        return all_healthy

    def run_tests(self, verbose: bool = True) -> bool:
        """Run the core integration test suite."""
        cmd = ["python", "-m", "pytest", str(self.test_file)]

        if verbose:
            cmd.extend(["-v", "-s"])

        cmd.extend(["--tb=short", "--no-header"])

        print(f"🚀 Running command: {' '.join(cmd)}")
        print()

        result = subprocess.run(cmd, cwd=self.project_root)
        return result.returncode == 0

    async def run_core_integration_tests(self) -> bool:
        """Run the complete core integration test suite."""
        print("🚀 APEXSIGMA CORE INTEGRATION TEST RUNNER")
        print("Testing InGest-LLM.as → memOS.as Integration")
        print("=" * 60)

        # Step 1: Validate services
        services_ready = await self.validate_services()

        if not services_ready:
            print("❌ Core services are not ready - integration tests cannot run")
            return False

        print(f"⏰ Starting integration tests at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Step 2: Run tests
        success = self.run_tests()

        if success:
            print("\n🎉 Core integration tests completed successfully!")
            print("✅ InGest-LLM.as → memOS.as integration is working correctly")
        else:
            print("\n💥 Some integration tests failed!")
            print("❌ Check the output above for details")

        return success


async def main():
    """Main entry point."""
    runner = CoreIntegrationTestRunner()

    try:
        success = await runner.run_core_integration_tests()

        if success:
            print("\n🏆 All core integration tests passed!")
            sys.exit(0)
        else:
            print("\n🔧 Integration tests revealed issues that need attention.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️  Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Test runner encountered an error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
