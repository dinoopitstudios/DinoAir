# DinoAir Performance and Telemetry API

This document describes the stable public API for DinoAir's performance monitoring and telemetry collection system.

## Overview

The DinoAir API provides two main capabilities:

1. **Performance Monitoring** - Track operation execution times, memory usage, and custom metrics
2. **Telemetry Export** - Opt-in export of performance data with memory bounds to prevent leaks

## Core Classes

### PerformanceMonitor

The `PerformanceMonitor` class provides performance tracking capabilities:

```python
from utils.dinoair_api import PerformanceMonitor, PerformanceConfig

# Create monitor with custom config
config = PerformanceConfig(enabled=True, max_metrics_retained=1000)
monitor = PerformanceMonitor(config)

# Start/end operations manually
operation_id = monitor.start_operation("data_processing", user_id="123")
# ... do work ...
metrics = monitor.end_operation(operation_id)

# Use context manager (recommended)
with monitor.monitor_operation("file_upload") as operation_id:
    # ... upload file ...
    pass
```

### TelemetryManager

The `TelemetryManager` class handles opt-in telemetry export:

```python
from utils.dinoair_api import TelemetryManager, TelemetryConfig

# Create manager with custom config
config = TelemetryConfig(
    enabled=True,
    export_format="json",
    export_destination="file",
    output_file="telemetry.json",
    max_total_metrics=10000
)
manager = TelemetryManager(config)

# Enable/disable dynamically
manager.enable(export_format="prometheus", output_file="metrics.prom")
manager.disable()

# Force immediate export
success = manager.force_export()
```

## Global Functions

For convenience, the API provides global functions that work with singleton instances:

### Performance Monitoring

```python
from utils.dinoair_api import (
    enable_performance_monitoring,
    disable_performance_monitoring,
    monitor_performance,
    performance_decorator,
    configure_performance
)

# Enable global monitoring
enable_performance_monitoring()

# Monitor operations with context manager
with monitor_performance("database_query") as operation_id:
    # ... query database ...
    pass

# Use decorator for automatic monitoring
@performance_decorator("expensive_calculation")
def calculate_result(data):
    # ... complex calculation ...
    return result

# Configure global settings
configure_performance(enabled=True, max_metrics_retained=500)
```

### Telemetry

```python
from utils.dinoair_api import (
    enable_telemetry,
    disable_telemetry,
    export_telemetry,
    configure_telemetry
)

# Enable telemetry with file export
enable_telemetry(
    export_format="json",
    export_destination="file",
    output_file="performance_data.json"
)

# Enable telemetry with HTTP export
enable_telemetry(
    export_format="json",
    export_destination="http",
    http_endpoint="https://metrics.example.com/api/telemetry"
)

# Configure additional settings
configure_telemetry(
    max_total_metrics=20000,
    export_interval_seconds=30,
    retention_hours=48
)

# Force export and disable
export_telemetry()
disable_telemetry()
```

## Configuration

### PerformanceConfig

```python
@dataclass
class PerformanceConfig:
    enabled: bool = True
    sampling_rate: float = 1.0  # 0.0-1.0, percentage of operations to monitor
    max_metrics_retained: int = 1000
    enable_memory_tracking: bool = True
    enable_cpu_tracking: bool = True
    threshold_duration_ms: float = 100.0  # Log warnings for slow operations
    include_system_info: bool = False
```

### TelemetryConfig

```python
@dataclass
class TelemetryConfig:
    enabled: bool = False  # Opt-in by default
    export_interval_seconds: float = 60.0
    max_metrics_per_operation: int = 100  # Memory bound per operation
    max_total_metrics: int = 10000  # Total memory bound
    batch_size: int = 500
    export_format: str = "json"  # json, prometheus, csv
    export_destination: str = "file"  # file, http, console
    output_file: Optional[str] = None
    http_endpoint: Optional[str] = None
    include_system_metrics: bool = True
    include_custom_metrics: bool = True
    retention_hours: float = 24.0
```

## Export Formats

### JSON Format

```json
{
  "metrics": [
    {
      "operation": "data_processing",
      "duration": 0.153,
      "memory_usage": 1048576,
      "cpu_usage": 15.3,
      "timestamp": 1699123456.789,
      "custom_metrics": {
        "records_processed": 1000,
        "errors": 0
      }
    }
  ]
}
```

### Prometheus Format

```
# HELP dinoair_operation_duration_seconds Duration of operations in seconds
# TYPE dinoair_operation_duration_seconds gauge
dinoair_operation_duration_seconds{operation="data_processing"} 0.153 1699123456789

# HELP dinoair_operation_memory_bytes Memory usage in bytes
# TYPE dinoair_operation_memory_bytes gauge
dinoair_operation_memory_bytes{operation="data_processing"} 1048576 1699123456789
```

## Memory Management

The telemetry system includes comprehensive memory bounds to prevent leaks:

1. **Per-Operation Limits** - Each operation type has a maximum buffer size
2. **Total Memory Limits** - Global cap on all buffered metrics
3. **Automatic Cleanup** - Old metrics are automatically removed based on retention policy
4. **Bounded Collections** - Uses `deque` with `maxlen` for memory-efficient storage

```python
# Configure memory bounds
configure_telemetry(
    max_metrics_per_operation=100,  # Per operation type
    max_total_metrics=10000,        # Total across all operations
    retention_hours=24.0,           # Auto-cleanup after 24 hours
    batch_size=500                  # Export batch size
)
```

## Integration Examples

### Basic Usage

```python
from utils.dinoair_api import enable_performance_monitoring, enable_telemetry, monitor_performance

# Enable both systems
enable_performance_monitoring()
enable_telemetry(export_destination="console")

# Monitor a process
with monitor_performance("file_processing") as operation_id:
    process_large_file("data.csv")
```

### Advanced Configuration

```python
from utils.dinoair_api import PerformanceConfig, TelemetryConfig, PerformanceMonitor, TelemetryManager

# Custom performance config
perf_config = PerformanceConfig(
    enabled=True,
    sampling_rate=0.1,  # Sample 10% of operations
    max_metrics_retained=5000,
    threshold_duration_ms=50.0
)

# Custom telemetry config
telemetry_config = TelemetryConfig(
    enabled=True,
    export_format="prometheus",
    export_destination="file",
    output_file="/var/log/dinoair/metrics.prom",
    export_interval_seconds=30,
    max_total_metrics=50000,
    retention_hours=72.0
)

# Create configured instances
monitor = PerformanceMonitor(perf_config)
telemetry = TelemetryManager(telemetry_config)
```

### Production Setup

```python
import os
from utils.dinoair_api import enable_performance_monitoring, enable_telemetry

# Enable performance monitoring in production
enable_performance_monitoring()

# Configure telemetry based on environment
if os.getenv("TELEMETRY_ENABLED", "false").lower() == "true":
    telemetry_endpoint = os.getenv("TELEMETRY_ENDPOINT")
    if telemetry_endpoint:
        enable_telemetry(
            export_format="json",
            export_destination="http",
            http_endpoint=telemetry_endpoint,
            export_interval_seconds=60,
            max_total_metrics=20000
        )
    else:
        enable_telemetry(
            export_format="json",
            export_destination="file",
            output_file="/var/log/dinoair/telemetry.json"
        )
```

## Error Handling

The API is designed to be resilient and fail gracefully:

- If internal modules are unavailable, operations become no-ops
- Export failures are logged but don't interrupt application flow
- Memory bounds prevent runaway resource usage
- Invalid configurations fall back to safe defaults

```python
# Safe to call even if telemetry is disabled or unavailable
result = export_telemetry()  # Returns False if export fails

# Monitor operations continue to work even if backend is unavailable
with monitor_performance("critical_operation") as op_id:
    # This will always execute, monitoring is best-effort
    critical_business_logic()
```

## Migration Guide

### From Internal APIs

If you were previously using internal performance monitoring functions, update your imports:

```python
# Old (internal)
from utils.performance_monitor import get_performance_monitor, enable_performance_monitoring

# New (public API)
from utils.dinoair_api import get_performance_monitor, enable_performance_monitoring
```

### Testing with Public API

Update your tests to use only the public API:

```python
# Old (internal)
from utils.performance_monitor import PerformanceMonitor

# New (public API)
from utils.dinoair_api import PerformanceMonitor
```

## Best Practices

1. **Always use context managers** for operation monitoring when possible
2. **Configure appropriate memory bounds** for your use case
3. **Use decorators** for consistent function-level monitoring
4. **Monitor telemetry metrics count** to ensure memory bounds are working
5. **Test with telemetry disabled** to ensure graceful degradation
6. **Use structured operation names** for better telemetry organization

## Troubleshooting

### Performance Issues

- Check sampling rate if overhead is too high
- Reduce `max_metrics_retained` if memory usage is high
- Disable CPU/memory tracking if not needed

### Telemetry Issues

- Check export destination accessibility (file permissions, HTTP endpoint)
- Verify export format is supported by your monitoring system
- Monitor telemetry logs for export failures
- Use `force_export()` to test export functionality

### Memory Issues

- Reduce `max_total_metrics` and `max_metrics_per_operation`
- Decrease `retention_hours` for faster cleanup
- Monitor metrics count with `get_metrics_count()`
