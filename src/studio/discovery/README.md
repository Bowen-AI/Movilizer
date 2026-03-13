# Model Auto-Discovery Agent

The Model Auto-Discovery agent periodically scans HuggingFace for better open-weight models across multiple task categories and automatically integrates superior candidates into the Movilizer workspace.

## Architecture

### Components

#### 1. Scanner (`scanner.py`)
Scans HuggingFace API for models matching task requirements.

**Features:**
- Queries HuggingFace API with filters for task type, license, downloads, privacy
- Supports task categories: text-to-image, text-to-video, text-generation, text-to-speech, text-to-audio
- Scores candidates by: `likes * recency + downloads * popularity`
- Filters for open licenses (MIT, Apache 2.0, CC-BY-4.0, OpenRAIL, etc.)
- Minimum download thresholds to ensure model quality
- Recency boost (2.0x for fresh models, decaying to 0.5x)

**Key Classes:**
- `HFModelScanner`: Main scanner with configurable thresholds
- `ModelCandidate`: Dataclass representing a candidate model
- `ScanResult`: Result of scanning a task category

**Usage:**
```python
from studio.discovery import HFModelScanner

scanner = HFModelScanner(timeout=30)
result = scanner.scan_task_category(
    "text-to-image",
    limit_per_task=50,
    sort="trending"
)

# Get all candidates for a task
for candidate in result.candidates[:5]:
    print(f"{candidate.repo_id}: score={candidate.score:.2f}")

# Scan all categories
all_results = scanner.scan_all_categories()
```

#### 2. Benchmark Runner (`benchmark.py`)
Downloads and evaluates candidate models against standardized benchmarks.

**Features:**
- Downloads candidate models to temporary cache
- Runs task-specific benchmarks:
  - Generation time measurement
  - GPU VRAM usage tracking
  - Quality scoring via task-specific metrics
- Compares candidates against current active models
- Configurable thresholds for quality, VRAM, and time
- Saves detailed benchmark results

**Thresholds:**
- Quality score: minimum 0.70 (0-1 scale)
- VRAM usage: maximum 10GB
- Generation time: maximum 5 minutes
- Integration threshold: 0.75 (candidate score)

**Key Classes:**
- `BenchmarkRunner`: Runs benchmarks with task-specific implementations
- `BenchmarkResult`: Detailed benchmark metrics and pass/fail status

**Benchmark Methods:**
- `_benchmark_text_to_image()`: Image generation quality and performance
- `_benchmark_text_to_video()`: Video generation quality and performance
- `_benchmark_text_generation()`: LLM inference speed and accuracy
- `_benchmark_text_to_speech()`: TTS quality and synthesis speed
- `_benchmark_text_to_audio()`: Audio/music generation quality

**Usage:**
```python
from studio.discovery import BenchmarkRunner

runner = BenchmarkRunner(timeout=600)
result = runner.benchmark_candidate(
    repo_id="stabilityai/stable-diffusion-xl-base-1.0",
    task="text-to-image",
    cache_root=Path("models/cache")
)

if result.passed:
    print(f"Score: {result.score:.2f}, Quality: {result.quality_score:.2f}")
```

#### 3. Integrator (`integrator.py`)
Pulls passing models into permanent cache and updates workspace configuration.

**Features:**
- Pulls candidate models to permanent cache (using existing `pull_model`)
- Updates workspace configuration with new models
- Runs validation pipeline to ensure model integrity
- Generates migration reports with full audit trail
- Supports rollback (stub for future implementation)

**Integration Process:**
1. Check benchmark score >= threshold (0.75)
2. Pull model to cache using `studio.models.registry.pull_model`
3. Update workspace YAML config with new model reference
4. Run validation checks (file existence, format validation)
5. Save migration report with full details

**Key Classes:**
- `ModelIntegrator`: Orchestrates integration workflow
- `IntegrationResult`: Integration status and details

**Usage:**
```python
from studio.discovery import ModelIntegrator
from pathlib import Path

integrator = ModelIntegrator(
    cache_root=Path("models/cache"),
    workspace_config_path=Path("workspace.yaml")
)

result = integrator.integrate_candidate(
    repo_id="stabilityai/stable-diffusion-xl-base-1.0",
    task="text-to-image",
    benchmark_result=benchmark_result
)

if result.integrated:
    print(f"Model integrated: {result.model_path}")
```

#### 4. Scheduler (`scheduler.py`)
Manages periodic discovery and benchmarking with configurable intervals.

**Features:**
- Periodic scan scheduling (default: daily)
- Periodic benchmark scheduling (default: weekly)
- Threading-based implementation for background operation
- State persistence (timestamps, intervals, errors)
- Manual trigger capability
- Error tracking and recovery
- Thread-safe operations with locking

**State Management:**
- Tracks last scan and benchmark timestamps
- Persists to YAML file for recovery
- Allows configurable intervals
- Records last error for debugging

**Scheduling Modes:**
- Automatic: Background daemon with timer-based checks
- Manual: Trigger scan/benchmark on demand
- State-based: Persisted state survives restarts

**Key Classes:**
- `DiscoveryScheduler`: Main scheduler with threading
- `ScheduleState`: Persistent state dataclass

**Usage:**
```python
from studio.discovery import DiscoveryScheduler

config = {
    "scan_interval_hours": 24,
    "benchmark_interval_hours": 168,
    "check_interval_seconds": 3600,
}

scheduler = DiscoveryScheduler(
    config=config,
    state_file=Path("discovery/state.yaml")
)

# Register callbacks
scheduler.register_scan_callback(my_scan_function)
scheduler.register_benchmark_callback(my_benchmark_function)

# Start background scheduler
scheduler.start()

# Check status
status = scheduler.get_status()
print(f"Active task: {status['active_task']}")

# Manual triggers
scheduler.trigger_scan()
scheduler.trigger_benchmark()

# Cleanup
scheduler.stop()
```

## Configuration

Configuration file: `configs/discovery/default.yaml`

```yaml
# Overall enable/disable
enabled: true

# HuggingFace API settings
huggingface:
  api_base: "https://huggingface.co/api/models"
  api_timeout: 30
  models_per_task: 50
  sort_by: "trending"

# Scanner thresholds
scanner:
  min_downloads: 100
  min_likes: 0
  open_licenses_only: true
  exclude_private: true

# Benchmark settings
benchmark:
  quality_threshold: 0.70
  vram_threshold_mb: 10240
  time_threshold_sec: 300
  integration_threshold: 0.75
  timeout_sec: 600

# Task categories
tasks:
  text-to-image: true
  text-to-video: true
  text-generation: true
  text-to-speech: true
  text-to-audio: true

# Scheduling
schedule:
  enabled: true
  scan_interval_hours: 24
  benchmark_interval_hours: 168
  check_interval_seconds: 3600

# Output
output:
  cache_root: "models/cache"
  results_dir: "discovery/results"
  state_file: "discovery/state.yaml"
  log_level: "INFO"

# Integration
integration:
  update_workspace_config: true
  run_validation: true
  save_migration_reports: true
```

## Workflow

### Discovery Cycle

```
1. SCAN PHASE (Daily)
   └─> Query HuggingFace for each task
   └─> Filter & score candidates
   └─> Return ranked list

2. BENCHMARK PHASE (Weekly)
   └─> Pull candidates to test cache
   └─> Run task-specific benchmarks
   └─> Compare vs current models
   └─> Save benchmark results

3. INTEGRATION PHASE (On Pass)
   └─> Check score >= threshold
   └─> Pull to permanent cache
   └─> Update workspace config
   └─> Validate model files
   └─> Save migration report

4. SCHEDULE PHASE (Continuous)
   └─> Background scheduler
   └─> Trigger based on intervals
   └─> Persist state
   └─> Track errors
```

## Task Categories

The scanner supports these task categories:

| Category | HF Tasks |
|----------|----------|
| text-to-image | text-to-image, image-generation |
| text-to-video | text-to-video, video-generation |
| text-generation | text-generation |
| text-to-speech | text-to-speech, tts |
| text-to-audio | text-to-audio, audio-generation, music-generation |

## Scoring Algorithm

Candidates are scored based on:

```
score = (likes + 1)^0.5 * recency_boost + (downloads/100 + 1)^0.5
```

Where `recency_boost` ranges from 0.5x to 2.0x:
- 2.0x for models updated today
- Linear decay to 1.0x at 90 days
- Further decay to 0.5x at 1 year

This prevents very popular but outdated models from dominating.

## License Filtering

Models must have one of these licenses:
- MIT, Apache 2.0, BSD variants
- GPL variants, AGPL
- CC-BY-4.0, CC-BY-SA-4.0, CC0-1.0
- OpenRAIL, OpenRAIL++
- None (no license specified)

Proprietary and restrictive licenses are excluded.

## Example Usage

See `example_usage.py` for complete examples:

```bash
python3 src/studio/discovery/example_usage.py
```

## Integration with Workspace

The integrator updates the workspace config as follows:

```yaml
models:
  text-to-image:
    repo_id: stabilityai/stable-diffusion-xl-base-1.0
    path: models/cache/stabilityai__stable-diffusion-xl-base-1.0
    integrated_at: 2026-03-12T17:05:00+00:00
```

## Error Handling

- Network errors: Logged and skipped, scheduler continues
- Benchmark failures: Detailed error in BenchmarkResult
- Integration failures: Rollback support (future)
- State persistence: Recovers from restarts

## Performance Considerations

- **Scan time**: ~30 seconds per task category
- **Benchmark time**: 5-600 seconds depending on model size
- **API rate limiting**: Respects HuggingFace rate limits
- **Memory**: Uses local_files_only=True to avoid redundant downloads

## Future Enhancements

- [ ] Async benchmarking for parallel evaluation
- [ ] Integration rollback implementation
- [ ] Custom benchmark plugins
- [ ] Model performance telemetry
- [ ] Web UI for monitoring
- [ ] Email notifications on upgrades
- [ ] A/B testing framework
