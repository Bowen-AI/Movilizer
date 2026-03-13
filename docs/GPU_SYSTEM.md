# GPU Resource Management System

Complete GPU discovery, allocation, and monitoring system for the Movilizer AI movie studio.

## Overview

The GPU resource management system provides:

- **GPU Discovery**: Detect all available GPUs (A100 80GB, A100 40GB, consumer GPUs) with full details
- **GPU Allocation**: Intelligent scheduling of models to GPUs with multi-GPU sharding support
- **Continuous Monitoring**: Real-time health tracking, thermal monitoring, and utilization metrics
- **Automatic Rebalancing**: Triggers rebalancing when thermal or utilization issues detected

## Architecture

### Modules

```
src/studio/gpu/
├── __init__.py      # Public API exports
├── discovery.py     # GPU detection (nvidia-smi, torch.cuda, pynvml)
├── allocator.py     # GPU allocation and scheduling
└── monitor.py       # Continuous monitoring and health tracking
```

## Quick Start

### GPU Discovery

```python
from src.studio.gpu import GPUDiscovery

discovery = GPUDiscovery()
gpus = discovery.get_gpus()

for gpu in gpus:
    print(f"GPU {gpu.index}: {gpu.name}")
    print(f"  VRAM: {gpu.vram_total_gb}GB")
    print(f"  Free: {gpu.vram_free_gb}GB")
    print(f"  Compute Capability: {gpu.compute_capability_major}.{gpu.compute_capability_minor}")
```

### GPU Allocation

```python
from src.studio.gpu import GPUAllocator, ModelType

allocator = GPUAllocator()

# Allocate for a single task
allocation = allocator.allocate(
    task_id="inference-1",
    model_type=ModelType.SDXL_BASE,
    gpus=gpus,
)

# Or plan allocation for multiple tasks
plan = allocator.plan_allocations(
    tasks=[
        ("task-1", ModelType.SDXL_BASE, None),
        ("task-2", ModelType.CLIP_VISION, None),
        ("task-3", ModelType.UPSCALER, None),
    ],
    gpus=gpus,
)

if plan.is_feasible():
    for alloc in plan.allocations:
        print(f"Task {alloc.task_id} -> GPUs {alloc.gpu_indices}")
```

### GPU Monitoring

```python
from src.studio.gpu import MonitoredGPUCluster

# Start monitoring
cluster = MonitoredGPUCluster(poll_interval_sec=5.0)
cluster.start()

# Register rebalancing callback
def on_rebalance(health_report):
    print(f"Rebalancing needed: {health_report.summary}")

cluster.register_rebalance_callback(on_rebalance)

# Get current state
health = cluster.get_health_report()
metrics = cluster.get_metrics(gpu_index=0)

# Stop monitoring
cluster.stop()
```

## Discovery

### Detection Chain

GPU discovery tries multiple methods in this order:

1. **nvidia-smi** (most reliable, works without Python deps)
   - Parses nvidia-smi subprocess output
   - Gets full GPU details: memory, compute capability, power, temperature
   - Works even if CUDA libraries not available

2. **torch.cuda** (requires PyTorch)
   - Uses PyTorch CUDA API
   - Gets compute capability and memory info
   - Useful when nvidia-smi unavailable

3. **pynvml** (requires pynvml package)
   - Uses NVIDIA Management Library
   - Gets full GPU details similar to nvidia-smi
   - Fallback option

### GPU Info Details

```python
gpu.index                      # GPU index
gpu.name                       # GPU model name
gpu.uuid                       # GPU UUID
gpu.vram_total_gb             # Total VRAM (GB)
gpu.vram_used_gb              # Used VRAM (GB)
gpu.vram_free_gb              # Free VRAM (GB)
gpu.vram_utilization_pct      # Utilization (0-100%)
gpu.compute_capability_major  # Compute capability major version
gpu.compute_capability_minor  # Compute capability minor version
gpu.power_draw_w              # Current power draw (watts)
gpu.power_limit_w             # Power limit (watts)
gpu.temperature_c             # GPU temperature (Celsius)
gpu.is_a100_80gb             # Check if A100 80GB
gpu.is_a100_40gb             # Check if A100 40GB
```

## Allocation

### Model VRAM Profiles

Built-in profiles for common models:

| Model | VRAM | Sharding | Max Batch |
|-------|------|----------|-----------|
| SDXL Base | 6.5GB | Yes | 1 |
| SDXL Refiner | 4.5GB | Yes | 1 |
| SDXL LoRA | 0.5GB | No | 1 |
| SDXL ControlNet | 2.0GB | Yes | 1 |
| FLUX Dev | 10.0GB | Yes | 1 |
| FLUX Pro | 20.0GB | Yes | 1 |
| CLIP Vision | 1.5GB | No | 4 |
| Face Detection | 0.3GB | No | 32 |
| Face Recognition | 0.5GB | No | 16 |
| Upscaler | 2.0GB | Yes | 2 |

### Custom Profiles

```python
from src.studio.gpu import ModelVRAMProfile, ModelType, GPUAllocator

# Create custom profile
profile = ModelVRAMProfile(
    model_type=ModelType.CUSTOM,
    vram_required_gb=12.0,
    supports_sharding=True,
    max_batch_size=2,
    description="My custom diffusion model",
)

# Register with allocator
allocator = GPUAllocator()
allocator.vram_registry.register(profile)

# Use in allocation
allocation = allocator.allocate(
    task_id="custom-task",
    model_type=ModelType.CUSTOM,
    gpus=gpus,
)
```

### Allocation Algorithm

Best-fit allocation strategy:

1. **Single GPU Allocation** (preferred)
   - Try to fit model on a single GPU
   - No sharding overhead
   - Sorted by free VRAM (largest first)

2. **Multi-GPU Sharding** (if supported and needed)
   - Greedy packing across multiple GPUs
   - Used when model > single GPU VRAM
   - Automatically tracks across GPU indices

```python
allocation = allocator.allocate(
    task_id="task-1",
    model_type=ModelType.SDXL_BASE,
    gpus=gpus,
    custom_vram_gb=8.0,  # Override default
)

# Allocation details
allocation.gpu_indices        # List of assigned GPU indices
allocation.vram_required_gb   # VRAM needed
allocation.vram_allocated_gb  # VRAM allocated
allocation.uses_sharding      # Multi-GPU sharding used
```

### Allocation Planning

Plan allocation for multiple tasks:

```python
plan = allocator.plan_allocations(
    tasks=[
        ("task-1", ModelType.SDXL_BASE, None),
        ("task-2", ModelType.CLIP_VISION, 2.0),  # Custom VRAM
        ("task-3", ModelType.UPSCALER, None),
    ],
    gpus=gpus,
)

# Check results
if plan.is_feasible():
    print("All tasks allocated!")
    print(f"Total VRAM used: {plan.total_vram_allocated_gb():.1f}GB")
else:
    print("Some tasks failed:")
    for task_id, reason in plan.failed_allocations:
        print(f"  {task_id}: {reason}")
```

## Monitoring

### Health Tracking

The monitoring system tracks:

- **VRAM Utilization**: Current usage percentage
- **Temperature**: GPU temperature (if available)
- **Power Draw**: Current power consumption
- **Historical Metrics**: Last N samples per GPU

### Health Report

```python
health = cluster.get_health_report()

health.healthy_gpus          # Number of healthy GPUs
health.total_gpus            # Total GPUs
health.overheated_gpus       # GPUs exceeding 85°C
health.throttled_gpus        # GPUs at 75-85°C
health.underutilized_gpus    # GPUs with <5% utilization
health.overutilized_gpus     # GPUs with >90% utilization
health.needs_rebalancing     # Rebalancing recommended
health.summary               # Human-readable summary
```

### Metrics History

```python
metrics_buf = cluster.get_metrics(gpu_index=0)

# Get all historical data
history = metrics_buf.get_history()

# Get averages over last N samples
avg_util = metrics_buf.avg_vram_utilization_pct(last_n=10)
avg_temp = metrics_buf.avg_temperature_c(last_n=10)
max_temp = metrics_buf.max_temperature_c(last_n=10)

# Each sample contains
for metrics in history:
    metrics.vram_utilization_pct  # Utilization %
    metrics.power_draw_w          # Power (watts)
    metrics.temperature_c         # Temperature (C)
    metrics.timestamp             # When recorded
    metrics.is_critical_temp      # >= 85°C
    metrics.is_high_temp          # >= 75°C
    metrics.is_fully_utilized     # >= 90%
    metrics.is_idle               # < 5%
```

### Rebalancing Callbacks

```python
def on_rebalance_needed(health_report):
    """Handle rebalancing trigger."""
    if health_report.overheated_gpus:
        print(f"Emergency cooling: GPUs {health_report.overheated_gpus}")
        # Pause heavy tasks on overheated GPUs

    if health_report.underutilized_gpus and health_report.overutilized_gpus:
        print("Rebalancing workload distribution")
        # Redistribute tasks

cluster.register_rebalance_callback(on_rebalance_needed)
```

## Configuration

See `configs/gpu/default.yaml` for all configuration options:

```yaml
discovery:
  preferred_methods:
    - nvidia-smi
    - torch_cuda
    - pynvml

monitoring:
  poll_interval_sec: 5.0
  history_size: 120
  temp_warning_c: 75.0
  temp_critical_c: 85.0
  util_idle_pct: 5.0
  util_high_pct: 90.0

allocation:
  models:
    sdxl_base:
      vram_gb: 6.5
      max_batch_size: 1
      supports_sharding: true

rebalancing:
  enabled: true
  triggers:
    on_thermal_critical: true
    on_utilization_skew: true
    skew_threshold_pct: 50.0
  strategy: best_fit
```

## Examples

See `examples/gpu_management_example.py` for complete working examples:

- GPU discovery and details
- Single and multi-task allocation
- Custom model profiles
- Continuous monitoring
- Rebalancing callbacks

## Advanced Usage

### Multi-GPU Sharding

For models larger than single GPU VRAM:

```python
# FLUX Pro (20GB) on two 16GB GPUs
allocation = allocator.allocate(
    task_id="flux-task",
    model_type=ModelType.FLUX_PRO,
    gpus=[
        GPUInfo(..., vram_total_gb=16),
        GPUInfo(..., vram_total_gb=16),
    ]
)

print(f"Sharded across {allocation.num_gpus} GPUs")
```

### Context Manager

```python
with MonitoredGPUCluster(poll_interval_sec=5.0) as cluster:
    gpus = cluster.get_gpus()
    health = cluster.get_health_report()
    # Auto-stops on exit
```

### Memory Reservation

System automatically reserves memory for:
- CUDA context and runtime overhead
- Buffer space for allocation safety

Configure in `default.yaml`:
```yaml
reservation:
  system_vram_gb: 0.5   # Fixed overhead
  buffer_pct: 5.0       # 5% buffer
```

## Troubleshooting

### No GPUs Detected

1. Check nvidia-smi is installed:
   ```bash
   which nvidia-smi
   ```

2. Verify CUDA installation:
   ```bash
   nvidia-smi
   ```

3. Try fallback methods:
   ```python
   discovery = GPUDiscovery()
   print(f"nvidia-smi: {discovery._nvidia_smi_path}")
   print(f"torch.cuda: {discovery._has_torch_cuda}")
   print(f"pynvml: {discovery._has_pynvml}")
   ```

### Allocation Failures

1. Check available VRAM:
   ```python
   for gpu in gpus:
       print(f"GPU {gpu.index}: {gpu.vram_free_gb:.1f}GB free")
   ```

2. Try with custom lower VRAM requirement:
   ```python
   allocation = allocator.allocate(
       task_id="task",
       model_type=ModelType.SDXL_BASE,
       gpus=gpus,
       custom_vram_gb=5.0,  # Lower than default
   )
   ```

3. Enable sharding:
   ```python
   # Model automatically uses sharding if needed
   # Check allocation.uses_sharding
   ```

### Monitor Thread Issues

1. Stop cleanly:
   ```python
   cluster.stop(timeout_sec=10)
   ```

2. Check logging:
   ```python
   from src.studio.utils import setup_logging
   setup_logging("DEBUG")
   ```

## Performance Considerations

- **Discovery**: ~1 second for nvidia-smi parsing
- **Allocation**: O(n log n) where n = number of GPUs
- **Monitoring**: ~1-5% CPU overhead at 5s poll interval
- **Memory**: ~10MB per GPU in historical buffer (120 samples)

## Thread Safety

All components are thread-safe:
- `GPUMonitor` runs in dedicated daemon thread
- Allocation operations use RLock for safety
- Safe to call from multiple threads

## Logging

Enable debug logging:

```python
from src.studio.utils import setup_logging
setup_logging("DEBUG")
```

Logs go to logger named `studio.gpu.*`:
```
2024-03-12 12:34:56 | INFO  | studio.gpu.discovery | Discovered 2 GPU(s) via nvidia-smi
2024-03-12 12:34:57 | INFO  | studio.gpu.allocator | Allocated: GPUAllocation(task=...)
2024-03-12 12:34:58 | INFO  | studio.gpu.monitor   | GPU monitor started (poll_interval=5.0s)
```

## Implementation Details

### GPU Discovery Fallback Chain

The discovery system tries multiple methods:

1. **nvidia-smi subprocess** (recommended)
   - No Python dependencies
   - Robust parsing of CSV output
   - Comprehensive GPU information
   - Timeout protection (10 seconds)

2. **torch.cuda** (if PyTorch installed)
   - Direct CUDA API access
   - GPU memory info
   - Limited to what PyTorch exposes

3. **pynvml** (if pynvml installed)
   - NVIDIA Management Library
   - Similar to nvidia-smi but via Python
   - Good fallback option

### Allocation Algorithm Details

**Best-fit strategy**:
1. Sort GPUs by free VRAM (largest first)
2. Try single GPU (faster, less overhead)
3. If fails and sharding supported, try multi-GPU (greedy pack)
4. Return None if no feasible allocation

**Time complexity**: O(n log n) where n = number of GPUs

### Monitor Architecture

```
MonitoredGPUCluster
├── GPUMonitor (thread)
│   ├── GPUDiscovery
│   └── MetricsBuffer[GPU0, GPU1, ...]
└── Callbacks (rebalancing triggers)
```

**Update cycle** (every poll_interval):
1. Discover current GPU state
2. Create metrics snapshots
3. Add to history buffers
4. Evaluate cluster health
5. Trigger callbacks if needed

## API Reference

### GPUInfo

```python
@dataclass
class GPUInfo:
    index: int
    name: str
    uuid: str
    vram_total_gb: float
    vram_used_mb: float
    vram_free_mb: float
    compute_capability_major: int
    compute_capability_minor: int
    power_draw_w: Optional[float] = None
    power_limit_w: Optional[float] = None
    temperature_c: Optional[float] = None
```

### GPUAllocator

```python
class GPUAllocator:
    def allocate(
        task_id: str,
        model_type: ModelType,
        gpus: list[GPUInfo],
        custom_vram_gb: Optional[float] = None,
    ) -> GPUAllocation

    def plan_allocations(
        tasks: list[tuple[str, ModelType, Optional[float]]],
        gpus: list[GPUInfo],
    ) -> AllocationPlan

    def deallocate(task_id: str) -> bool
    def get_allocation(task_id: str) -> Optional[GPUAllocation]
    def get_allocations() -> dict[str, GPUAllocation]
```

### GPUMonitor

```python
class GPUMonitor:
    def start() -> None
    def stop(timeout_sec: float = 10.0) -> bool
    def register_rebalance_callback(callback: Callable) -> None
    def get_gpus() -> list[GPUInfo]
    def get_metrics(gpu_index: int) -> Optional[MetricsBuffer]
    def get_latest_health_report() -> Optional[HealthReport]
    def refresh() -> list[GPUInfo]
```

## Testing

Run tests:

```bash
cd /sessions/loving-determined-cray/mnt/Movilizer
python -m pytest tests/test_gpu_system.py -v
```

See `tests/test_gpu_system.py` for comprehensive test examples.

## Future Enhancements

- [ ] GPU thermal profiling and prediction
- [ ] Cost-aware allocation (budget constraints)
- [ ] Dynamic model quantization based on available VRAM
- [ ] GPU affinity and NUMA awareness
- [ ] Integration with job scheduler (SLURM, K8s)
- [ ] Multi-node GPU cluster management
