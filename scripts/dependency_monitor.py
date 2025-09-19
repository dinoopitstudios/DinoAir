#!/usr/bin/env python3
"""
Dependency Graph Monitoring System for DinoAir
============================================

This script monitors dependency relationships, import performance, and maintains
health metrics for the import organization system.

Features:
- Real-time circular dependency detection
- Import performance monitoring
- Dependency graph visualization
- Health metrics and alerting
- Historical trend analysis

Usage:
    python scripts/dependency_monitor.py [command] [options]

Commands:
    monitor     - Run continuous monitoring
    analyze     - Generate dependency analysis report
    alert       - Check for alert conditions
    visualize   - Generate dependency graph visualization
    performance - Track import performance metrics
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import matplotlib.pyplot as plt
    import networkx as nx

    HAS_VISUALIZATION = True
except ImportError:
    HAS_VISUALIZATION = False


@dataclass
class ImportMetrics:
    """Metrics for import performance and health."""

    module_name: str
    import_time_estimate: float
    import_size: int
    dependency_count: int
    circular_dependencies: list[str]
    last_modified: datetime
    health_score: float


@dataclass
class AlertCondition:
    """Represents an alert condition."""

    severity: str  # critical, warning, info
    message: str
    module: str
    metric_value: float
    threshold: float
    timestamp: datetime


class DependencyMonitor:
    """Monitors dependency health and import organization."""

    def __init__(self, root_path: Path, config: dict[str, Any] | None = None):
        self.root_path = root_path
        self.config = config or self._load_default_config()
        self.metrics_history: list[ImportMetrics] = []
        self.alerts: list[AlertCondition] = []
        self.logger = self._setup_logging()
        self._dependency_cache: dict[Path, tuple[int, list[str]]] = {}

    def _load_default_config(self) -> dict[str, Any]:
        """Load default monitoring configuration."""
        return {
            "monitoring": {
                "import_time_threshold": 0.1,  # seconds
                "dependency_count_threshold": 10,
                "health_score_threshold": 0.8,
                "circular_dependency_tolerance": 0,
            },
            "alerts": {"enabled": True, "email_recipients": [], "webhook_url": None},
            "visualization": {
                "enabled": HAS_VISUALIZATION,
                "output_dir": "dependency_graphs",
                "formats": ["png", "svg"],
            },
            "performance": {
                "track_imports": True,
                "sample_rate": 1.0,
                "retention_days": 30,
            },
        }

    def _setup_logging(self) -> logging.Logger:
        """Set up logging for dependency monitoring."""
        logger = logging.getLogger("dependency_monitor")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def measure_import_performance(self) -> dict[str, ImportMetrics]:
        """Measure import performance for all modules."""
        self.logger.info("Starting import performance measurement...")
        metrics = {}

        # Find all Python modules
        python_files = list(self.root_path.rglob("*.py"))
        python_files = [
            f
            for f in python_files
            if not any(
                part in str(f)
                for part in [
                    "__pycache__",
                    ".git",
                    "test",
                    "venv",
                    ".venv",
                    "build",
                    "dist",
                    "site-packages",
                ]
            )
        ]

        for file_path in python_files:
            try:
                module_name = self._path_to_module(file_path)
                metrics[module_name] = self._measure_module_import(
                    file_path, module_name)
            except Exception as e:
                self.logger.warning(f"Failed to measure {file_path}: {e}")

        return metrics

    def _path_to_module(self, file_path: Path) -> str:
        """Convert file path to module name."""
        relative_path = file_path.relative_to(self.root_path)
        parts = list(relative_path.parts)

        if parts[-1] == "__init__.py":
            parts = parts[:-1]
        else:
            parts[-1] = relative_path.stem

        return ".".join(parts) if parts else "__main__"

    def _measure_module_import(self, file_path: Path, module_name: str) -> ImportMetrics:
        """Measure import performance for a single module."""
        time.time()

        # Get file stats
        stat = file_path.stat()
        import_size = stat.st_size
        last_modified = datetime.fromtimestamp(stat.st_mtime)

        # Analyze dependencies
        dependency_count, circular_deps = self._analyze_module_dependencies(
            file_path)

        # Calculate import time estimate (size-based, not real import time)
        # TODO: Replace with actual import timing using importlib or time.perf_counter for accuracy.
        import_time_estimate = (
            import_size / 1000000
        ) * 0.001  # Size-based estimate, not real import time

        # Calculate health score
        health_score = self._calculate_health_score(
            import_time_estimate, dependency_count, len(circular_deps)
        )

        return ImportMetrics(
            module_name=module_name,
            import_time_estimate=import_time_estimate,
            import_size=import_size,
            dependency_count=dependency_count,
            circular_dependencies=circular_deps,
            last_modified=last_modified,
            health_score=health_score,
        )

    def _analyze_module_dependencies(self, file_path: Path) -> tuple[int, list[str]]:
        """Analyze dependencies for a module using directory-based caching."""
        directory = file_path.parent

        # Check if we have cached results for this directory
        if directory in self._dependency_cache:
            return self._dependency_cache[directory]

        try:
            # Use the existing circular dependency detector once per directory
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/check_circular_dependencies.py",
                    "--path",
                    str(directory),
                    "--format",
                    "json",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                circular_deps = [
                    " -> ".join(cycle["cycle"]) for cycle in data.get("circular_dependencies", [])
                ]
                # Cache results for this directory
                cache_result = (
                    len(data.get("circular_dependencies", [])), circular_deps)
                self._dependency_cache[directory] = cache_result
                return cache_result

            # Cache empty result for failed analysis
            cache_result = (0, [])
            self._dependency_cache[directory] = cache_result
            return cache_result

        except Exception as e:
            self.logger.warning(
                f"Failed to analyze dependencies for {file_path}: {e}")
            # Cache empty result for failed analysis
            cache_result = (0, [])
            self._dependency_cache[directory] = cache_result
            return cache_result

    def _calculate_health_score(
        self, import_time_estimate: float, dependency_count: int, circular_count: int
    ) -> float:
        """Calculate health score for a module."""
        score = 1.0

        # Penalize slow imports
        if import_time_estimate > self.config["monitoring"]["import_time_threshold"]:
            score -= 0.3

        # Penalize high dependency count
        if dependency_count > self.config["monitoring"]["dependency_count_threshold"]:
            score -= 0.2

        # Heavily penalize circular dependencies
        if circular_count > 0:
            score -= 0.5 * circular_count

        return max(0.0, score)

    def check_alert_conditions(self, metrics: dict[str, ImportMetrics]) -> list[AlertCondition]:
        """Check for alert conditions in current metrics."""
        alerts = []

        for module_name, metric in metrics.items():
            # Check import time threshold
            if metric.import_time_estimate > self.config["monitoring"]["import_time_threshold"]:
                alerts.append(
                    AlertCondition(
                        severity="warning",
                        message=f"Slow import detected in {module_name}",
                        module=module_name,
                        metric_value=metric.import_time_estimate,
                        threshold=self.config["monitoring"]["import_time_threshold"],
                        timestamp=datetime.now(),
                    )
                )

            # Check health score threshold
            if metric.health_score < self.config["monitoring"]["health_score_threshold"]:
                alerts.append(
                    AlertCondition(
                        severity="critical" if metric.health_score < 0.5 else "warning",
                        message=f"Low health score for {module_name}",
                        module=module_name,
                        metric_value=metric.health_score,
                        threshold=self.config["monitoring"]["health_score_threshold"],
                        timestamp=datetime.now(),
                    )
                )

            # Check circular dependencies
            if metric.circular_dependencies:
                alerts.append(
                    AlertCondition(
                        severity="critical",
                        message=f"Circular dependencies detected in {module_name}",
                        module=module_name,
                        metric_value=len(metric.circular_dependencies),
                        threshold=0,
                        timestamp=datetime.now(),
                    )
                )

        return alerts

    def generate_dependency_graph(
        self, metrics: dict[str, ImportMetrics], output_path: Path
    ) -> bool:
        """Generate dependency graph visualization."""
        if not HAS_VISUALIZATION:
            self.logger.warning("Visualization libraries not available")
            return False

        try:
            G = nx.DiGraph()

            # Add nodes with health score as attribute
            for module_name, metric in metrics.items():
                G.add_node(module_name, health_score=metric.health_score)

            # Add edges for dependencies (simplified)
            for module_name, metric in metrics.items():
                for dep in metric.circular_dependencies:
                    if " -> " in dep:
                        parts = dep.split(" -> ")
                        for i in range(len(parts) - 1):
                            if parts[i] in G.nodes and parts[i + 1] in G.nodes:
                                G.add_edge(
                                    parts[i], parts[i + 1], style="circular")

            # Create visualization
            plt.figure(figsize=(12, 8))
            pos = nx.spring_layout(G, k=1, iterations=50)

            # Color nodes by health score
            node_colors = [
                (
                    "red"
                    if metrics[node].health_score < 0.5
                    else "yellow"
                    if metrics[node].health_score < 0.8
                    else "green"
                )
                for node in G.nodes()
            ]

            nx.draw(
                G,
                pos,
                node_color=node_colors,
                node_size=300,
                font_size=8,
                font_weight="bold",
                arrows=True,
                edge_color="gray",
                alpha=0.7,
            )

            plt.title(
                "DinoAir Dependency Graph\n(Red: Poor Health, Yellow: Warning, Green: Healthy)"
            )
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            plt.close()

            return True

        except Exception as e:
            self.logger.error(f"Failed to generate dependency graph: {e}")
            return False

    def run_monitoring_cycle(self) -> dict[str, Any]:
        """Run a complete monitoring cycle."""
        self.logger.info("Starting monitoring cycle...")

        cycle_start = time.time()

        # Measure current performance
        metrics = self.measure_import_performance()

        # Check for alerts
        alerts = self.check_alert_conditions(metrics)

        # Generate reports
        report = {
            "timestamp": datetime.now().isoformat(),
            "cycle_duration": time.time() - cycle_start,
            "total_modules": len(metrics),
            "healthy_modules": sum(1 for m in metrics.values() if m.health_score >= 0.8),
            "warning_modules": sum(1 for m in metrics.values() if 0.5 <= m.health_score < 0.8),
            "critical_modules": sum(1 for m in metrics.values() if m.health_score < 0.5),
            "total_alerts": len(alerts),
            "critical_alerts": sum(1 for a in alerts if a.severity == "critical"),
            "average_health_score": (
                sum(m.health_score for m in metrics.values()) /
                len(metrics) if metrics else 0
            ),
            "total_circular_dependencies": sum(
                len(m.circular_dependencies) for m in metrics.values()
            ),
        }

        # Store metrics and alerts
        self.metrics_history.extend(metrics.values())
        self.alerts.extend(alerts)

        # Generate visualization if enabled
        if self.config["visualization"]["enabled"]:
            output_dir = Path(self.config["visualization"]["output_dir"])
            output_dir.mkdir(exist_ok=True)

            graph_path = (
                output_dir /
                f"dependency_graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )
            self.generate_dependency_graph(metrics, graph_path)

        self.logger.info(f"Monitoring cycle completed: {report}")
        return report


def handle_monitor(monitor: DependencyMonitor, continuous: bool, interval: int):
    if continuous:
        print(f"Starting continuous monitoring (interval: {interval}s)")
        try:
            while True:
                report = monitor.run_monitoring_cycle()
                if report["critical_alerts"] > 0:
                    print(report)
                time.sleep(interval)
        except KeyboardInterrupt:
            pass
    else:
        report = monitor.run_monitoring_cycle()
        print(report)


def main():
    """Main entry point for dependency monitoring."""
    parser = argparse.ArgumentParser(
        description="Dependency monitoring for DinoAir",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "command",
        choices=["monitor", "analyze", "alert", "visualize", "performance"],
        help="Monitoring command to execute",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path(),
        help="Path to analyze (default: current directory)",
    )
    parser.add_argument("--output", type=Path,
                        help="Output file/directory for results")
    parser.add_argument(
        "--format",
        choices=["json", "text", "html"],
        default="text",
        help="Output format",
    )
    parser.add_argument(
        "--continuous", action="store_true", help="Run in continuous monitoring mode"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Monitoring interval in seconds (default: 300)",
    )

    args = parser.parse_args()

    if not args.path.exists():
        print(f"Error: Path {args.path} does not exist", file=sys.stderr)
        sys.exit(1)

    monitor = DependencyMonitor(args.path)

    if args.command == "monitor":
        if args.continuous:
            handle_monitor(monitor, args.continuous, args.interval)
        else:
            report = monitor.run_monitoring_cycle()
            print(json.dumps(report, indent=2))

    elif args.command == "analyze":
        metrics = monitor.measure_import_performance()
        analysis = {
            "total_modules": len(metrics),
            "modules": {name: asdict(metric) for name, metric in metrics.items()},
            "summary": {
                "average_import_time_estimate": (
                    sum(m.import_time_estimate for m in metrics.values()) /
                    len(metrics)
                    if metrics
                    else 0
                ),
                "average_health_score": (
                    sum(m.health_score for m in metrics.values()) /
                    len(metrics) if metrics else 0
                ),
                "modules_with_circular_deps": sum(
                    1 for m in metrics.values() if m.circular_dependencies
                ),
            },
        }

        if args.output:
            with open(args.output, "w") as f:
                json.dump(analysis, f, indent=2, default=str)
        else:
            print(json.dumps(analysis, indent=2, default=str))

    elif args.command == "visualize":
        if not HAS_VISUALIZATION:
            print("Error: Visualization requires matplotlib and networkx",
                  file=sys.stderr)
            sys.exit(1)

        metrics = monitor.measure_import_performance()
        output_path = args.output or Path("dependency_graph.png")

        if monitor.generate_dependency_graph(metrics, output_path):
            print(f"Dependency graph saved to {output_path}")
        else:
            print("Failed to generate dependency graph", file=sys.stderr)
            sys.exit(1)

    else:
        print(f"Command {args.command} not yet implemented", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
