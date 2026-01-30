"""
API Contract Validator for Soma Ecosystem

Validates that all services are responding according to their defined contracts.
Used by start_ecosystem.ps1 to ensure service stability before connecting components.
"""

import json
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx


class ContractValidator:
    """Validates service contracts against running instances."""

    def __init__(self, contracts_dir: str = "D:\\projects\\Soma\\contracts"):
        self.contracts_dir = Path(contracts_dir)
        self.contracts = self._load_contracts()
        self.validation_results = {}

    def _load_contracts(self) -> Dict[str, Dict[str, Any]]:
        """Load all contract JSON files."""
        contracts = {}

        if not self.contracts_dir.exists():
            raise FileNotFoundError(
                f"Contracts directory not found: {self.contracts_dir}"
            )

        for contract_file in self.contracts_dir.glob("*_contract.json"):
            service_name = contract_file.stem.replace("_contract", "")
            try:
                with open(contract_file, "r", encoding="utf-8") as f:
                    contracts[service_name] = json.load(f)
            except Exception as e:
                print(f"Error loading contract {contract_file}: {e}")

        return contracts

    async def validate_service(
        self, service_name: str, timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Validate a single service against its contract.

        Args:
            service_name: Name of the service (e.g., 'ingress', 'ingest')
            timeout: Request timeout in seconds

        Returns:
            Validation result dictionary
        """
        if service_name not in self.contracts:
            return {
                "service": service_name,
                "valid": False,
                "error": "Contract not found",
            }

        contract = self.contracts[service_name]
        health_check = contract.get("health_check", {})

        endpoint = health_check.get("endpoint", "/health")
        expected_status = health_check.get("expected_status_code", 200)
        port = contract.get("endpoints", {}).get("capture_server", {}).get("port")

        if not port:
            port = self._get_service_port(service_name)

        url = f"http://localhost:{port}{endpoint}"

        result = {
            "service": service_name,
            "url": url,
            "valid": False,
            "error": None,
            "response": None,
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)

                result["response"] = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                }

                if response.status_code == expected_status:
                    try:
                        response_data = response.json()
                        result["response"]["body"] = response_data

                        if self._validate_response_schema(
                            service_name, response_data, contract
                        ):
                            result["valid"] = True
                        else:
                            result["error"] = "Response schema validation failed"
                    except json.JSONDecodeError:
                        result["error"] = "Response is not valid JSON"
                else:
                    result["error"] = f"Unexpected status code: {response.status_code}"

        except httpx.ConnectError:
            result["error"] = "Connection refused - service not running"
        except asyncio.TimeoutError:
            result["error"] = f"Request timed out after {timeout}s"
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"

        self.validation_results[service_name] = result
        return result

    def _get_service_port(self, service_name: str) -> int:
        """Get default port for a service."""
        port_map = {
            "ingress": 8000,
            "ingest": 8766,
            "omegakg": 8765,
            "memos": 8768,
            "cortex": 5173,
        }
        return port_map.get(service_name.lower(), 8000)

    def _validate_response_schema(
        self, service_name: str, response_data: Any, contract: Dict[str, Any]
    ) -> bool:
        """
        Validate response against contract schema.

        For now, just check that response has required fields.
        Can be expanded with full schema validation (e.g., using pydantic).
        """
        if not isinstance(response_data, dict):
            return False

        health_endpoint = contract.get("endpoints", {}).get("health", {})
        expected_response = health_endpoint.get("response", {})

        for key in expected_response.keys():
            if key not in response_data:
                return False

        return True

    async def validate_all(
        self, services: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate multiple services.

        Args:
            services: List of service names to validate. If None, validates all.

        Returns:
            Summary of validation results
        """
        if services is None:
            services = list(self.contracts.keys())

        tasks = [self.validate_service(service) for service in services]
        results = await asyncio.gather(*tasks)

        valid_count = sum(1 for r in results if r["valid"])
        total_count = len(results)

        return {
            "total": total_count,
            "valid": valid_count,
            "invalid": total_count - valid_count,
            "results": results,
            "success": valid_count == total_count,
        }

    def print_summary(self, summary: Dict[str, Any]) -> None:
        """Print validation summary to console."""
        print("\n" + "=" * 60)
        print("Soma Ecosystem Contract Validation")
        print("=" * 60)

        for result in summary["results"]:
            status = "✅ VALID" if result["valid"] else "❌ INVALID"
            print(f"\n{status}: {result['service'].upper()}")
            print(f"  URL: {result['url']}")

            if result["valid"]:
                print(f"  Status Code: {result['response']['status_code']}")
            else:
                print(f"  Error: {result['error']}")

        print("\n" + "=" * 60)
        print(f"Summary: {summary['valid']}/{summary['total']} services valid")
        print("=" * 60)

        if summary["success"]:
            print("✅ All services are responding correctly")
        else:
            print("⚠️  Some services are not ready")


async def main():
    """Main entry point for contract validation."""
    import sys

    validator = ContractValidator()

    if len(sys.argv) > 1:
        services = sys.argv[1:]
    else:
        services = None

    summary = await validator.validate_all(services)
    validator.print_summary(summary)

    sys.exit(0 if summary["success"] else 1)


if __name__ == "__main__":
    asyncio.run(main())
