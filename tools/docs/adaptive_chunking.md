# Adaptive chunking (experimental)

## 1. Overview

Adaptive chunking dynamically adjusts the size of streaming chunks based on observed processing latency and backpressure signals. It can improve overall throughput while keeping per‑chunk latency near a target. This feature is experimental and off by default; when disabled, the system uses the baseline fixed chunk size and behavior unchanged.

## 2. Enabling the feature

- Config: set [StreamingConfig.adaptive_chunking_enabled](pseudocode_translator/config.py:258) to true (for example in your YAML under streaming).
- Environment overrides (env wins over file config):
  - PSEUDOCODE_STREAMING_ADAPTIVE_ENABLED
  - PSEUDOCODE_STREAMING_ADAPTIVE_TARGET_MS
  - PSEUDOCODE_STREAMING_ADAPTIVE_MIN_SIZE
  - PSEUDOCODE_STREAMING_ADAPTIVE_MAX_SIZE
  - PSEUDOCODE_STREAMING_ADAPTIVE_HYSTERESIS
  - PSEUDOCODE_STREAMING_ADAPTIVE_COOLDOWN
  - PSEUDOCODE_STREAMING_ADAPTIVE_ALPHA
  - PSEUDOCODE_STREAMING_ADAPTIVE_INITIAL

Note: You can combine config and env; final values are validated and applied at runtime.

## 3. Configuration reference

The following fields live under streaming in the config and control adaptive behavior:

| Field                                                              | Default                                                                                | Description                                                                            |
| ------------------------------------------------------------------ | -------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| [adaptive_chunking_enabled](pseudocode_translator/config.py:258)   | False                                                                                  | Feature flag; if false, the pipeline uses the baseline fixed chunk size.               |
| [adaptive_target_latency_ms](pseudocode_translator/config.py:259)  | 600                                                                                    | Target per‑chunk latency in milliseconds (ms).                                         |
| [adaptive_min_chunk_size](pseudocode_translator/config.py:260)     | 200                                                                                    | Minimum chunk size (characters).                                                       |
| [adaptive_max_chunk_size](pseudocode_translator/config.py:261)     | 2000                                                                                   | Maximum chunk size (characters).                                                       |
| [adaptive_hysteresis_pct](pseudocode_translator/config.py:262)     | 0.2                                                                                    | Fractional hysteresis band (e.g., 0.2 → ±20%) to reduce oscillation.                   |
| [adaptive_cooldown_chunks](pseudocode_translator/config.py:263)    | 3                                                                                      | Number of chunks to hold size steady after a change.                                   |
| [adaptive_smoothing_alpha](pseudocode_translator/config.py:264)    | 0.2                                                                                    | Exponential smoothing factor for observed latency (0 < alpha ≤ 1).                     |
| [adaptive_initial_chunk_size](pseudocode_translator/config.py:265) | None → falls back to [StreamingConfig.chunk_size](pseudocode_translator/config.py:236) | Optional starting size; if None, the controller initializes from the fixed chunk size. |

Validation and clamping:

- Config validation happens in [StreamingConfig.validate()](pseudocode_translator/config.py:272). In strict mode, invalid settings raise; in lenient mode, errors are returned and the system may proceed with defaults.
- At runtime, the controller clamps sizes to [min, max] via [AdaptiveChunkSizer.\_clamp()](pseudocode_translator/streaming/adaptive.py:235).

## 4. How it works

The controller [AdaptiveChunkSizer](pseudocode_translator/streaming/adaptive.py:48) tracks recent per‑chunk latency and adjusts size using:

- Smoothing: Exponential smoothing of observed latency in [AdaptiveChunkSizer.update_feedback()](pseudocode_translator/streaming/adaptive.py:132) with alpha = [adaptive_smoothing_alpha](pseudocode_translator/config.py:264).
- Hysteresis bands: Upper/lower bounds around the target in [AdaptiveChunkSizer.get_next_chunk_size()](pseudocode_translator/streaming/adaptive.py:166); changes only when outside the band.
- Cooldown: After any change, decisions are frozen for [adaptive_cooldown_chunks](pseudocode_translator/config.py:263) chunks.
- Bounded step changes: Size changes are ~20% per decision by default (see step_pct=0.2 in [AdaptiveChunkSizer.**init**()](pseudocode_translator/streaming/adaptive.py:83)).
- Backpressure guard: Increases are suppressed when queue utilization ≥ 80% ([AdaptiveChunkSizer.get_next_chunk_size()](pseudocode_translator/streaming/adaptive.py:211)).
- Optional TPS ceiling: If the model exposes tokens‑per‑second, new size is capped (see ceiling logic in [AdaptiveChunkSizer.get_next_chunk_size()](pseudocode_translator/streaming/adaptive.py:219)).

Units: latency in milliseconds; chunk size in characters (bytes of the source text).

## 5. Events and telemetry

- Event: [EventType.STREAM_ADAPTATION_DECISION](pseudocode_translator/integration/events.py:50) emitted by the pipeline when the size changes. Payload keys:
  - old_size, new_size, reason ("increase"/"decrease"), smoothed_latency_ms, target_latency_ms, backpressure_util, cooldown_remaining.
- Telemetry:
  - "adapt.decision" with counters adapt.increase/decrease/noop.
  - "adapt.latency_ms" with duration for smoothed or observed per‑chunk latency.
- Telemetry is disabled by default and is a no‑op unless enabled. Enable via env PSEUDOCODE_TELEMETRY=1; see [get_recorder()](pseudocode_translator/telemetry.py:293) and [telemetry_enabled()](pseudocode_translator/telemetry.py:81). Stability notes: see [docs/api_stability.md](docs/api_stability.md).

## 6. Benchmarking

A reproducible micro‑benchmark is provided in [examples/adaptive_benchmark.py](examples/adaptive_benchmark.py). Example runs:

- python examples/adaptive_benchmark.py --flag=0 --seed=123 --size=200000
- python examples/adaptive_benchmark.py --flag=1 --seed=123 --size=200000

The script prints a JSON summary including:

- throughput_bytes_per_s: Effective throughput.
- p50_ms, p95_ms: Median and 95th‑percentile latencies.
- decisions: Count of inc/dec/noop decisions.
- size_timeline: The chosen chunk size per iteration.

Look for higher throughput with acceptable p95 latency, and a stable size trajectory without oscillation.

## 7. Tuning guidance and safety

- Start with defaults. If your model/hardware can handle larger chunks, raise [adaptive_max_chunk_size](pseudocode_translator/config.py:261); if you see spikes above target, consider lowering [adaptive_min_chunk_size](pseudocode_translator/config.py:260) or the target.
- Set [adaptive_target_latency_ms](pseudocode_translator/config.py:259) to the per‑chunk latency you consider acceptable for interactive responsiveness.
- Keep [adaptive_hysteresis_pct](pseudocode_translator/config.py:262) around 0.2 to avoid oscillation; increase for more stability, decrease for more responsiveness.
- If jitter causes thrashing, increase [adaptive_cooldown_chunks](pseudocode_translator/config.py:263) slightly.
- Disabling the feature ([adaptive_chunking_enabled](pseudocode_translator/config.py:258)=false) reverts to baseline fixed‑size behavior.

## 8. Limitations

- Token‑to‑character mapping is approximate; chunk size is measured in characters.
- Natural latency jitter may cause occasional overshoot/undershoot despite smoothing and hysteresis.
- Increases are suppressed under high backpressure; adaptation may prefer stability over peak throughput in congested scenarios.

## 9. Pointers to source

- Controller: [pseudocode_translator/streaming/adaptive.py](pseudocode_translator/streaming/adaptive.py)
- Pipeline integration: [pseudocode_translator/streaming/pipeline.py](pseudocode_translator/streaming/pipeline.py)
- Config additions/validation: [pseudocode_translator/config.py](pseudocode_translator/config.py)
