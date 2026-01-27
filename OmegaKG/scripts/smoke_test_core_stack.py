#!/usr/bin/env python3
"""
Infrastructure Smoke Test Script
===============================

Automated infrastructure health monitoring for Phase 1 Discovery & Baseline.
Monitors Docker services, container health, and HTTP endpoints for 5+ minutes.

Usage:
    python scripts/smoke_test_core_stack.py [--duration 300] [--output reports/smoke_test_report.md]

Author: SigmaDev11
Date: 2025-12-12
Version: 1.0
"""

import json
import subprocess
import time
import requests
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timezone
import psutil


class InfrastructureSmokeTester:
    """Comprehensive infrastructure health monitoring."""

    def __init__(self, duration: int = 300):
        self.duration = duration  # seconds
        self.results = {
            "test_metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": duration,
                "version": "1.0",
            },
            "docker_status": {},
            "container_health": {},
            "endpoint_health": {},
            "system_resources": {},
            "crash_loops": {},
            "overall_status": "UNKNOWN",
        }

        # Services to monitor
        self.services = {
            "capture_server": {
                "name": "capture_server",
                "port": 8765,
                "endpoint": "http://localhost:8765/health",
            },
            "neo4j_browser": {
                "name": "neo4j",
                "port": 7474,
                "endpoint": "http://localhost:7474/",
            },
            "neo4j_bolt": {
                "name": "neo4j_bolt",
                "port": 7687,
                "endpoint": None,  # Bolt protocol, check port only
            },
            "postgres": {
                "name": "postgres",
                "port": 5433,
                "endpoint": None,  # Database protocol, check port only
            },
        }

        self.container_names = ["apexsigma.neo4j.db", "apexsigma.postgres.db"]

    def run_smoke_test(self) -> Dict[str, Any]:
        """Execute complete infrastructure smoke test."""
        print("🔍 Starting Infrastructure Smoke Test...")
        print(f"⏱️  Duration: {self.duration} seconds")

        start_time = time.time()
        end_time = start_time + self.duration

        # Phase 1: Docker status check
        self._check_docker_status()

        # Phase 2: Container health monitoring
        self._monitor_container_health()

        # Phase 3: Endpoint health monitoring
        self._monitor_endpoint_health(end_time)

        # Phase 4: System resources
        self._check_system_resources()

        # Phase 5: Crash loop detection
        self._detect_crash_loops()

        # Phase 6: Overall assessment
        self._assess_overall_status()

        print("✅ Infrastructure smoke test completed!")
        return self.results

    def _check_docker_status(self):
        """Check if Docker is running and accessible."""
        print("🐳 Checking Docker status...")

        try:
            result = subprocess.run(
                ["docker", "info"], capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                self.results["docker_status"] = {
                    "status": "RUNNING",
                    "output": result.stdout[:500],  # First 500 chars
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                print("   ✅ Docker is running")
            else:
                self.results["docker_status"] = {
                    "status": "ERROR",
                    "error": result.stderr,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                print("   ❌ Docker is not accessible")

        except subprocess.TimeoutExpired:
            self.results["docker_status"] = {
                "status": "TIMEOUT",
                "error": "Docker info command timed out",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            print("   ⏰ Docker check timed out")
        except Exception as e:
            self.results["docker_status"] = {
                "status": "ERROR",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            print(f"   ❌ Docker check failed: {e}")

    def _monitor_container_health(self):
        """Monitor container health for the entire duration."""
        print("📦 Monitoring container health...")

        container_stats = {}

        for container_name in self.container_names:
            try:
                result = subprocess.run(
                    [
                        "docker",
                        "ps",
                        "--filter",
                        f"name={container_name}",
                        "--format",
                        "json",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode == 0 and result.stdout.strip():
                    container_info = json.loads(result.stdout.strip())
                    container_stats[container_name] = {
                        "status": "RUNNING",
                        "info": container_info,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    print(f"   ✅ {container_name} is running")
                else:
                    container_stats[container_name] = {
                        "status": "NOT_FOUND",
                        "error": "Container not found",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    print(f"   ❌ {container_name} not found")

            except Exception as e:
                container_stats[container_name] = {
                    "status": "ERROR",
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                print(f"   ❌ Error checking {container_name}: {e}")

        self.results["container_health"] = container_stats

    def _monitor_endpoint_health(self, end_time: float):
        """Monitor HTTP endpoints throughout the test duration."""
        print("🌐 Monitoring endpoint health...")

        endpoint_stats = {}

        for service_name, service_config in self.services.items():
            if service_config["endpoint"] is None:
                continue  # Skip non-HTTP services

            endpoint_stats[service_name] = {
                "checks": [],
                "success_rate": 0.0,
                "avg_response_time": 0.0,
            }

            print(f"   📡 Monitoring {service_name} at {service_config['endpoint']}")

            # Check port availability first
            port_status = self._check_port(service_config["port"])
            if not port_status:
                print(
                    f"   ⚠️  Port {service_config['port']} not available for {service_name}"
                )
                continue

            # Monitor endpoint throughout duration
            check_count = 0
            success_count = 0
            total_response_time = 0

            while time.time() < end_time:
                check_start = time.time()

                try:
                    response = requests.get(service_config["endpoint"], timeout=5)

                    response_time = time.time() - check_start
                    check_count += 1
                    total_response_time += response_time

                    if response.status_code < 500:  # Accept 2xx, 3xx, 4xx as success
                        success_count += 1
                        status = "SUCCESS"
                    else:
                        status = "ERROR"

                    endpoint_stats[service_name]["checks"].append(
                        {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "status": status,
                            "status_code": response.status_code,
                            "response_time": response_time,
                            "content_length": len(response.content),
                        }
                    )

                except requests.exceptions.Timeout:
                    endpoint_stats[service_name]["checks"].append(
                        {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "status": "TIMEOUT",
                            "error": "Request timed out",
                        }
                    )
                except requests.exceptions.ConnectionError:
                    endpoint_stats[service_name]["checks"].append(
                        {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "status": "CONNECTION_ERROR",
                            "error": "Connection refused",
                        }
                    )
                except Exception as e:
                    endpoint_stats[service_name]["checks"].append(
                        {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "status": "ERROR",
                            "error": str(e),
                        }
                    )

                # Wait before the next check, ensuring not to exceed end_time
                remaining_time = end_time - time.time()
                sleep_duration = 10
                if remaining_time < sleep_duration:
                    break  # Not enough time for another full interval
                time.sleep(sleep_duration)

            # Calculate statistics
            if check_count > 0:
                endpoint_stats[service_name]["success_rate"] = (
                    success_count / check_count
                ) * 100
                endpoint_stats[service_name]["avg_response_time"] = (
                    total_response_time / check_count
                )

        self.results["endpoint_health"] = endpoint_stats

    def _check_port(self, port: int) -> bool:
        """Check if a port is available."""
        try:
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("localhost", port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _check_system_resources(self):
        """Check system resource usage."""
        print("💻 Checking system resources...")

        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()

            # Disk usage
            disk = psutil.disk_usage("/")

            # Network connections
            connections = len(psutil.net_connections())

            self.results["system_resources"] = {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "percent": memory.percent,
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent": round((disk.used / disk.total) * 100, 2),
                },
                "network_connections": connections,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            print(
                f"   📊 CPU: {cpu_percent}%, Memory: {memory.percent}%, Disk: {round((disk.used / disk.total) * 100, 2)}%"
            )

        except Exception as e:
            self.results["system_resources"] = {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            print(f"   ❌ System resource check failed: {e}")

    def _detect_crash_loops(self):
        """Detect container crash loops."""
        print("🔄 Checking for crash loops...")

        crash_loop_detection = {}

        for container_name in self.container_names:
            try:
                # Get container stats
                result = subprocess.run(
                    [
                        "docker",
                        "inspect",
                        container_name,
                        "--format",
                        "{{json .State}}",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode == 0:
                    state = json.loads(result.stdout)

                    crash_loop_detection[container_name] = {
                        "running": state.get("Running", False),
                        "restart_count": state.get("RestartCount", 0),
                        "started_at": state.get("StartedAt"),
                        "finished_at": state.get("FinishedAt"),
                        "exit_code": state.get("ExitCode"),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

                    if state.get("RestartCount", 0) > 0:
                        print(
                            f"   ⚠️  {container_name} has restarted {state.get('RestartCount')} times"
                        )
                    else:
                        print(f"   ✅ {container_name} has not restarted")

                else:
                    crash_loop_detection[container_name] = {
                        "error": "Container not found",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    print(f"   ❌ {container_name} not found")

            except Exception as e:
                crash_loop_detection[container_name] = {
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                print(f"   ❌ Error checking {container_name}: {e}")

        self.results["crash_loops"] = crash_loop_detection

    def _assess_overall_status(self):
        """Assess overall infrastructure health."""
        print("🎯 Assessing overall status...")

        # Criteria for success
        success_criteria = {
            "docker_running": self.results["docker_status"]["status"] == "RUNNING",
            "containers_running": all(
                status["status"] == "RUNNING"
                for status in self.results["container_health"].values()
            ),
            "endpoints_healthy": self._calculate_endpoint_health(),
            "no_crash_loops": self._check_no_crash_loops(),
        }

        # Count successful criteria
        successful_criteria = sum(success_criteria.values())
        total_criteria = len(success_criteria)

        if successful_criteria == total_criteria:
            self.results["overall_status"] = "HEALTHY"
            print("   ✅ All criteria met - Infrastructure is HEALTHY")
        elif successful_criteria >= total_criteria * 0.75:
            self.results["overall_status"] = "DEGRADED"
            print(
                f"   ⚠️  {successful_criteria}/{total_criteria} criteria met - Infrastructure is DEGRADED"
            )
        else:
            self.results["overall_status"] = "UNHEALTHY"
            print(
                f"   ❌ {successful_criteria}/{total_criteria} criteria met - Infrastructure is UNHEALTHY"
            )

        self.results["success_criteria"] = success_criteria

    def _calculate_endpoint_health(self) -> bool:
        """Calculate if endpoints are healthy based on success rate."""
        healthy_endpoints = 0
        total_endpoints = 0

        for service_name, stats in self.results["endpoint_health"].items():
            if stats["checks"]:  # Has checks
                total_endpoints += 1
                if stats["success_rate"] >= 90:  # 90% success rate
                    healthy_endpoints += 1

        return healthy_endpoints >= total_endpoints * 0.8  # 80% of endpoints healthy

    def _check_no_crash_loops(self) -> bool:
        """Check if there are no crash loops."""
        for container_stats in self.results["crash_loops"].values():
            if container_stats.get("restart_count", 0) > 0:
                return False
        return True

    def save_results(self, output_path: str = "reports/smoke_test_report.md"):
        """Save test results to markdown file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Generate markdown report
        report = self._generate_markdown_report()

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"💾 Report saved to: {output_file}")

    def _generate_markdown_report(self) -> str:
        """Generate markdown report from results."""
        report = f"""# Infrastructure Smoke Test Report

**Generated:** {self.results["test_metadata"]["timestamp"]}
**Duration:** {self.results["test_metadata"]["duration_seconds"]} seconds
**Overall Status:** {self.results["overall_status"]}

## Test Summary

| Criteria | Status | Details |
|----------|--------|---------|
| Docker Running | {"✅" if self.results["success_criteria"]["docker_running"] else "❌"} | Docker daemon accessible |
| Containers Running | {"✅" if self.results["success_criteria"]["containers_running"] else "❌"} | All required containers healthy |
| Endpoints Healthy | {"✅" if self.results["success_criteria"]["endpoints_healthy"] else "❌"} | HTTP endpoints responding |
| No Crash Loops | {"✅" if self.results["success_criteria"]["no_crash_loops"] else "❌"} | Containers not restarting |

## Docker Status

- **Status:** {self.results["docker_status"]["status"]}
- **Timestamp:** {self.results["docker_status"]["timestamp"]}

## Container Health

"""

        for container_name, stats in self.results["container_health"].items():
            report += f"### {container_name}\n"
            report += f"- **Status:** {stats['status']}\n"
            if "info" in stats:
                report += f"- **Running:** {stats['info'].get('State', {}).get('Running', 'Unknown')}\n"
            report += "\n"

        report += "## Endpoint Health\n\n"

        for service_name, stats in self.results["endpoint_health"].items():
            if stats["checks"]:
                report += f"### {service_name}\n"
                report += f"- **Success Rate:** {stats['success_rate']:.1f}%\n"
                report += (
                    f"- **Avg Response Time:** {stats['avg_response_time']:.3f}s\n"
                )
                report += f"- **Total Checks:** {len(stats['checks'])}\n\n"

        report += "## System Resources\n\n"
        if "error" not in self.results["system_resources"]:
            sr = self.results["system_resources"]
            report += f"- **CPU Usage:** {sr['cpu_percent']}%\n"
            report += f"- **Memory:** {sr['memory']['percent']}% ({sr['memory']['available_gb']:.1f}GB available)\n"
            report += f"- **Disk:** {sr['disk']['percent']}% ({sr['disk']['free_gb']:.1f}GB free)\n"
            report += f"- **Network Connections:** {sr['network_connections']}\n\n"

        report += "## Crash Loop Detection\n\n"
        for container_name, stats in self.results["crash_loops"].items():
            report += f"### {container_name}\n"
            if "error" not in stats:
                report += f"- **Running:** {stats['running']}\n"
                report += f"- **Restart Count:** {stats['restart_count']}\n"
                report += f"- **Exit Code:** {stats['exit_code']}\n\n"

        return report


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Infrastructure Smoke Test")
    parser.add_argument(
        "--duration",
        type=int,
        default=300,
        help="Test duration in seconds (default: 300)",
    )
    parser.add_argument(
        "--output", default="reports/smoke_test_report.md", help="Output file path"
    )

    args = parser.parse_args()

    try:
        tester = InfrastructureSmokeTester(args.duration)
        results = tester.run_smoke_test()
        tester.save_results(args.output)

        # Print summary
        print("\n" + "=" * 60)
        print("📋 PHASE 1 - TASK 1.2 SUMMARY")
        print("=" * 60)
        print(f"⏱️  Duration: {results['test_metadata']['duration_seconds']} seconds")
        print(f"🐳 Docker: {results['docker_status']['status']}")
        print(
            f"📦 Containers: {'✅ Healthy' if results['success_criteria']['containers_running'] else '❌ Issues'}"
        )
        print(
            f"🌐 Endpoints: {'✅ Healthy' if results['success_criteria']['endpoints_healthy'] else '❌ Issues'}"
        )
        print(
            f"🔄 Crash Loops: {'✅ None' if results['success_criteria']['no_crash_loops'] else '❌ Detected'}"
        )
        print(f"🎯 Overall: {results['overall_status']}")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"❌ Error during smoke test: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
