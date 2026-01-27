#!/usr/bin/env python3
"""
Embedding Model Efficiency Analyzer

This script connects to Langfuse to analyze embedding model performance
and generate efficiency comparison reports.
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List
from dataclasses import dataclass
from collections import defaultdict

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ingest_llm_as.observability.langfuse_client import get_langfuse_client


@dataclass
class ModelPerformanceMetrics:
    """Performance metrics for an embedding model."""

    model_name: str
    total_calls: int
    avg_chars_per_second: float
    avg_embedding_efficiency: float
    avg_duration_ms: float
    success_rate: float
    content_types: List[str]
    error_count: int


@dataclass
class ContentTypeAnalysis:
    """Analysis of model performance by content type."""

    content_type: str
    model_performance: Dict[str, ModelPerformanceMetrics]
    best_model: str
    avg_confidence: float


class EmbeddingEfficiencyAnalyzer:
    """Analyzer for embedding model efficiency using Langfuse data."""

    def __init__(self):
        """Initialize the analyzer."""
        self.langfuse_client = get_langfuse_client()
        if not self.langfuse_client.enabled:
            raise RuntimeError(
                "Langfuse is not enabled. Please configure Langfuse settings."
            )

    def analyze_model_performance(
        self, hours_back: int = 24
    ) -> List[ModelPerformanceMetrics]:
        """
        Analyze model performance over the specified time period.

        Args:
            hours_back: Number of hours to look back for analysis

        Returns:
            List[ModelPerformanceMetrics]: Performance metrics for each model
        """
        print(
            f"🔍 Analyzing embedding model performance for the last {hours_back} hours..."
        )

        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)

        try:
            # Fetch embedding generation traces
            traces = self.langfuse_client.client.fetch_traces(
                name="embedding_generation",
                from_timestamp=start_time,
                to_timestamp=end_time,
                limit=1000,
            )

            model_stats = defaultdict(
                lambda: {
                    "total_calls": 0,
                    "total_chars": 0,
                    "total_duration": 0,
                    "success_count": 0,
                    "error_count": 0,
                    "content_types": set(),
                    "efficiency_scores": [],
                    "chars_per_second_values": [],
                }
            )

            for trace in traces.data:
                if not trace.output:
                    continue

                model_name = trace.output.get("model_used", "unknown")
                success = trace.output.get("success", False)

                model_stats[model_name]["total_calls"] += 1
                model_stats[model_name]["content_types"].add(
                    trace.metadata.get("content_type", "unknown")
                    if trace.metadata
                    else "unknown"
                )

                if success:
                    model_stats[model_name]["success_count"] += 1

                    # Extract performance metrics
                    chars_per_second = trace.output.get("chars_per_second", 0)
                    duration_ms = trace.output.get("total_duration_ms", 0)

                    if chars_per_second > 0:
                        model_stats[model_name]["chars_per_second_values"].append(
                            chars_per_second
                        )

                    if duration_ms > 0:
                        model_stats[model_name]["total_duration"] += duration_ms

                    # Extract efficiency scores
                    for score in trace.scores:
                        if score.name == "embedding_efficiency":
                            model_stats[model_name]["efficiency_scores"].append(
                                score.value
                            )
                else:
                    model_stats[model_name]["error_count"] += 1

            # Convert to ModelPerformanceMetrics
            performance_metrics = []
            for model_name, stats in model_stats.items():
                if stats["total_calls"] == 0:
                    continue

                avg_chars_per_second = (
                    sum(stats["chars_per_second_values"])
                    / len(stats["chars_per_second_values"])
                    if stats["chars_per_second_values"]
                    else 0
                )

                avg_efficiency = (
                    sum(stats["efficiency_scores"]) / len(stats["efficiency_scores"])
                    if stats["efficiency_scores"]
                    else 0
                )

                avg_duration = (
                    stats["total_duration"] / stats["success_count"]
                    if stats["success_count"] > 0
                    else 0
                )

                success_rate = stats["success_count"] / stats["total_calls"]

                metrics = ModelPerformanceMetrics(
                    model_name=model_name,
                    total_calls=stats["total_calls"],
                    avg_chars_per_second=avg_chars_per_second,
                    avg_embedding_efficiency=avg_efficiency,
                    avg_duration_ms=avg_duration,
                    success_rate=success_rate,
                    content_types=list(stats["content_types"]),
                    error_count=stats["error_count"],
                )
                performance_metrics.append(metrics)

            # Sort by efficiency
            performance_metrics.sort(
                key=lambda x: x.avg_embedding_efficiency, reverse=True
            )

            print(
                f"✅ Analyzed {len(performance_metrics)} models with performance data"
            )
            return performance_metrics

        except Exception as e:
            print(f"❌ Error analyzing model performance: {e}")
            return []

    def analyze_content_type_performance(
        self, hours_back: int = 24
    ) -> List[ContentTypeAnalysis]:
        """
        Analyze model performance by content type.

        Args:
            hours_back: Number of hours to look back for analysis

        Returns:
            List[ContentTypeAnalysis]: Performance analysis by content type
        """
        print(
            f"📊 Analyzing content type performance for the last {hours_back} hours..."
        )

        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)

        try:
            # Fetch embedding generation traces
            traces = self.langfuse_client.client.fetch_traces(
                name="embedding_generation",
                from_timestamp=start_time,
                to_timestamp=end_time,
                limit=1000,
            )

            content_type_stats = defaultdict(
                lambda: defaultdict(
                    lambda: {
                        "calls": 0,
                        "success": 0,
                        "efficiency_scores": [],
                        "chars_per_second": [],
                        "duration_ms": [],
                    }
                )
            )

            for trace in traces.data:
                if not trace.output or not trace.metadata:
                    continue

                content_type = trace.metadata.get("content_type", "unknown")
                model_name = trace.output.get("model_used", "unknown")
                success = trace.output.get("success", False)

                content_type_stats[content_type][model_name]["calls"] += 1

                if success:
                    content_type_stats[content_type][model_name]["success"] += 1

                    # Extract metrics
                    chars_per_second = trace.output.get("chars_per_second", 0)
                    duration_ms = trace.output.get("total_duration_ms", 0)

                    if chars_per_second > 0:
                        content_type_stats[content_type][model_name][
                            "chars_per_second"
                        ].append(chars_per_second)

                    if duration_ms > 0:
                        content_type_stats[content_type][model_name][
                            "duration_ms"
                        ].append(duration_ms)

                    # Extract efficiency scores
                    for score in trace.scores:
                        if score.name == "embedding_efficiency":
                            content_type_stats[content_type][model_name][
                                "efficiency_scores"
                            ].append(score.value)

            # Process results
            content_analyses = []
            for content_type, model_stats in content_type_stats.items():
                model_performance = {}
                best_efficiency = 0
                best_model = "none"

                for model_name, stats in model_stats.items():
                    if stats["calls"] == 0:
                        continue

                    avg_efficiency = (
                        sum(stats["efficiency_scores"])
                        / len(stats["efficiency_scores"])
                        if stats["efficiency_scores"]
                        else 0
                    )

                    avg_chars_per_second = (
                        sum(stats["chars_per_second"]) / len(stats["chars_per_second"])
                        if stats["chars_per_second"]
                        else 0
                    )

                    avg_duration = (
                        sum(stats["duration_ms"]) / len(stats["duration_ms"])
                        if stats["duration_ms"]
                        else 0
                    )

                    success_rate = stats["success"] / stats["calls"]

                    metrics = ModelPerformanceMetrics(
                        model_name=model_name,
                        total_calls=stats["calls"],
                        avg_chars_per_second=avg_chars_per_second,
                        avg_embedding_efficiency=avg_efficiency,
                        avg_duration_ms=avg_duration,
                        success_rate=success_rate,
                        content_types=[content_type],
                        error_count=stats["calls"] - stats["success"],
                    )

                    model_performance[model_name] = metrics

                    if avg_efficiency > best_efficiency:
                        best_efficiency = avg_efficiency
                        best_model = model_name

                analysis = ContentTypeAnalysis(
                    content_type=content_type,
                    model_performance=model_performance,
                    best_model=best_model,
                    avg_confidence=best_efficiency,
                )
                content_analyses.append(analysis)

            print(f"✅ Analyzed {len(content_analyses)} content types")
            return content_analyses

        except Exception as e:
            print(f"❌ Error analyzing content type performance: {e}")
            return []

    def generate_efficiency_report(self, hours_back: int = 24) -> str:
        """
        Generate a comprehensive efficiency report.

        Args:
            hours_back: Number of hours to analyze

        Returns:
            str: Formatted efficiency report
        """
        model_metrics = self.analyze_model_performance(hours_back)
        content_analyses = self.analyze_content_type_performance(hours_back)

        report = []
        report.append("🎯 EMBEDDING MODEL EFFICIENCY REPORT")
        report.append("=" * 50)
        report.append(f"📅 Analysis Period: Last {hours_back} hours")
        report.append(f"🕒 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Overall Model Performance
        report.append("📊 OVERALL MODEL PERFORMANCE")
        report.append("-" * 30)
        if model_metrics:
            for i, metrics in enumerate(model_metrics, 1):
                report.append(f"{i}. {metrics.model_name}")
                report.append(
                    f"   📈 Efficiency Score: {metrics.avg_embedding_efficiency:.3f}"
                )
                report.append(
                    f"   ⚡ Speed: {metrics.avg_chars_per_second:.1f} chars/sec"
                )
                report.append(f"   ✅ Success Rate: {metrics.success_rate:.1%}")
                report.append(f"   📞 Total Calls: {metrics.total_calls}")
                report.append(
                    f"   🎯 Content Types: {', '.join(metrics.content_types)}"
                )
                report.append("")
        else:
            report.append("   No model performance data available")

        # Content Type Analysis
        report.append("🏷️  PERFORMANCE BY CONTENT TYPE")
        report.append("-" * 35)
        if content_analyses:
            for analysis in content_analyses:
                report.append(f"📁 {analysis.content_type.upper()}")
                report.append(f"   🥇 Best Model: {analysis.best_model}")
                report.append(f"   📊 Best Efficiency: {analysis.avg_confidence:.3f}")
                report.append("")

                # Show all models for this content type
                sorted_models = sorted(
                    analysis.model_performance.items(),
                    key=lambda x: x[1].avg_embedding_efficiency,
                    reverse=True,
                )
                for model_name, metrics in sorted_models:
                    report.append(
                        f"     • {model_name}: {metrics.avg_embedding_efficiency:.3f} "
                        f"({metrics.avg_chars_per_second:.1f} chars/sec)"
                    )
                report.append("")
        else:
            report.append("   No content type analysis data available")

        # Recommendations
        report.append("💡 OPTIMIZATION RECOMMENDATIONS")
        report.append("-" * 35)

        if model_metrics:
            best_model = model_metrics[0]
            worst_model = model_metrics[-1]

            report.append(
                f"✅ Best Overall: {best_model.model_name} "
                f"(Efficiency: {best_model.avg_embedding_efficiency:.3f})"
            )

            if len(model_metrics) > 1:
                report.append(
                    f"⚠️  Needs Attention: {worst_model.model_name} "
                    f"(Efficiency: {worst_model.avg_embedding_efficiency:.3f})"
                )

            # Check for performance issues
            for metrics in model_metrics:
                if metrics.success_rate < 0.9:
                    report.append(
                        f"🚨 High Error Rate: {metrics.model_name} "
                        f"({metrics.error_count} errors)"
                    )

                if metrics.avg_embedding_efficiency < 0.3:
                    report.append(
                        f"🐌 Low Efficiency: {metrics.model_name} "
                        f"(Consider optimization)"
                    )

        # Content type specific recommendations
        for analysis in content_analyses:
            if analysis.avg_confidence < 0.5:
                report.append(
                    f"📉 Content Type Issue: {analysis.content_type} "
                    f"shows low performance across all models"
                )

        report.append("")
        report.append("🔍 For detailed analysis, check the Langfuse dashboard")
        report.append("📊 Dashboard: docs/observability-dashboard.md")

        return "\n".join(report)

    def export_metrics_json(
        self, hours_back: int = 24, output_file: str = "embedding_metrics.json"
    ) -> bool:
        """
        Export metrics to JSON file for further analysis.

        Args:
            hours_back: Number of hours to analyze
            output_file: Output JSON file path

        Returns:
            bool: True if export successful
        """
        try:
            model_metrics = self.analyze_model_performance(hours_back)
            content_analyses = self.analyze_content_type_performance(hours_back)

            export_data = {
                "analysis_timestamp": datetime.now().isoformat(),
                "hours_analyzed": hours_back,
                "model_performance": [
                    {
                        "model_name": m.model_name,
                        "total_calls": m.total_calls,
                        "avg_chars_per_second": m.avg_chars_per_second,
                        "avg_embedding_efficiency": m.avg_embedding_efficiency,
                        "avg_duration_ms": m.avg_duration_ms,
                        "success_rate": m.success_rate,
                        "content_types": m.content_types,
                        "error_count": m.error_count,
                    }
                    for m in model_metrics
                ],
                "content_type_analysis": [
                    {
                        "content_type": a.content_type,
                        "best_model": a.best_model,
                        "avg_confidence": a.avg_confidence,
                        "model_performance": {
                            name: {
                                "total_calls": metrics.total_calls,
                                "avg_embedding_efficiency": metrics.avg_embedding_efficiency,
                                "avg_chars_per_second": metrics.avg_chars_per_second,
                                "success_rate": metrics.success_rate,
                            }
                            for name, metrics in a.model_performance.items()
                        },
                    }
                    for a in content_analyses
                ],
            }

            with open(output_file, "w") as f:
                json.dump(export_data, f, indent=2)

            print(f"📊 Metrics exported to {output_file}")
            return True

        except Exception as e:
            print(f"❌ Error exporting metrics: {e}")
            return False


def main():
    """Main function for the analyzer script."""
    print("🚀 Embedding Model Efficiency Analyzer")
    print("=" * 40)

    try:
        analyzer = EmbeddingEfficiencyAnalyzer()

        # Generate and display report
        hours_back = 24  # Analyze last 24 hours
        report = analyzer.generate_efficiency_report(hours_back)
        print(report)

        # Export metrics to JSON
        analyzer.export_metrics_json(hours_back, "embedding_efficiency_metrics.json")

        print("\n🎉 Analysis complete!")

    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
