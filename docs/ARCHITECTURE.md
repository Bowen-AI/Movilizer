# Movilizer Autonomous Movie Studio — System Architecture

## Vision

Movilizer is an autonomous AI movie studio that continuously generates Hollywood-quality
long-form movies from text and image prompts. It uses exclusively open-weight models,
discovers better models automatically, critiques every frame through a multi-agent
ensemble, and publishes finished movies to a Netflix-like streaming website.

---

## System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        MOVILIZER DAEMON                              │
│                                                                      │
│  ┌─────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────────┐  │
│  │ Story   │──▶│ Director │──▶│ Generate │──▶│ Multi-Agent      │  │
│  │ Writer  │   │ Agent    │   │ Pipeline │   │ Critique Ensemble│  │
│  └─────────┘   └──────────┘   └──────────┘   └────────┬─────────┘  │
│       ▲                                                │             │
│       │              ┌──────────────┐                  │             │
│       └──────────────│ Feedback Loop│◀─────────────────┘             │
│                      └──────────────┘                                │
│                                                                      │
│  ┌──────────────┐  ┌─────────────────┐  ┌────────────────────────┐  │
│  │ GPU Resource │  │ Model Discovery │  │ Website / Distribution │  │
│  │ Manager      │  │ Agent           │  │ Manager                │  │
│  └──────────────┘  └─────────────────┘  └────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 1. GPU Resource Manager (`src/studio/gpu/`)

Discovers and manages all available GPU resources on the host.

### Components

- **`discovery.py`** — Detects GPUs via nvidia-smi/torch.cuda, reports VRAM, compute
  capability, current utilization. Runs periodically (every 30s).
- **`allocator.py`** — Assigns models to GPUs based on VRAM requirements. Supports
  multi-GPU model sharding (tensor parallel) for large models.
- **`monitor.py`** — Continuous GPU utilization tracking. Triggers rebalancing when
  GPUs are under/over-utilized.

### GPU Assignment Strategy

```
Model VRAM Requirements (approx):
─────────────────────────────────
CogVideoX-2B:     ~8GB   → Any GPU
CogVideoX-5B:     ~20GB  → A100/4090
Wan2.1-14B:       ~40GB  → A100 (single) or 2x consumer
SDXL:             ~7GB   → Any GPU
Llama-3.1-8B:     ~16GB  → A100/4090
Llama-3.1-70B:    ~40GB  → A100 or 2x consumer (quantized)
Mistral-7B:       ~14GB  → A100/4090

Assignment Algorithm:
1. Enumerate GPUs → sort by free VRAM descending
2. For each pending task, find best-fit GPU(s)
3. If model > single GPU VRAM → use tensor parallel across GPUs
4. If no GPU available → queue task, retry when resources free
5. Prefer co-locating related tasks (same scene) on same GPU
```

### Resource Config (`configs/gpu/default.yaml`)

```yaml
gpu:
  poll_interval_sec: 30
  min_free_vram_mb: 2048       # reserve for system
  allow_multi_gpu_sharding: true
  prefer_dedicated_gpu_for_llm: true   # keep 1 GPU for critic LLMs
  max_concurrent_generations: 3
```

---

## 2. Model Discovery Agent (`src/studio/discovery/`)

Periodically scans model registries for better open-weight models.

### Components

- **`scanner.py`** — Queries HuggingFace API for models matching task tags
  (text-to-video, text-to-image, text-generation). Filters by license (open-weight),
  downloads, likes, recency.
- **`benchmark.py`** — Downloads candidate models, runs standardized benchmarks
  (speed, quality score via judges, VRAM usage). Compares against current models.
- **`integrator.py`** — If a candidate outperforms current model, updates
  model_registry and workspace config. Writes migration report.
- **`scheduler.py`** — Cron-like scheduling (default: daily scan, weekly benchmark).

### Discovery Pipeline

```
1. SCAN (daily)
   ├─ Query HF API: task=text-to-video, sort=trending, license=open
   ├─ Filter: min_downloads > 1000, updated < 30 days
   ├─ Score: likes * recency_weight + downloads * popularity_weight
   └─ Output: candidates.json (top 5 per task)

2. BENCHMARK (weekly, or on new candidate)
   ├─ Download candidate to temp cache
   ├─ Run standard test suite:
   │   ├─ 3 test prompts (action, dialog, landscape)
   │   ├─ Measure: generation time, VRAM peak, judge scores
   │   └─ Compare against current model on same prompts
   ├─ Score: quality_improvement * speed_factor / vram_factor
   └─ Output: benchmark_report.json

3. INTEGRATE (if benchmark passes threshold)
   ├─ Pull model to permanent cache
   ├─ Update workspace.yaml model references
   ├─ Run validation pipeline (1 test scene)
   └─ If validation passes → promote to active
```

### Tracked Model Categories

| Category | Current Default | Alternatives Scanned |
|----------|----------------|---------------------|
| Text-to-Video | CogVideoX-5B | Wan2.1, AnimateDiff, ModelScope |
| Text-to-Image | SDXL 1.0 | Flux, Playground v2.5, PixArt |
| Image-to-Video | CogVideoX-5B-I2V | Stable Video Diffusion, Wan2.1-I2V |
| Story/Script LLM | Llama-3.1-8B | Mistral, Qwen2.5, DeepSeek |
| Critique LLM | Llama-3.1-8B | Mistral, Qwen2.5 |
| TTS | Bark | XTTS-v2, Parler-TTS |
| Music | MusicGen | Stable Audio Open |
| Upscaling | Real-ESRGAN | SUPIR, Topaz (if open) |

---

## 3. Multi-Agent Critique System (`src/studio/critics/`)

Every generated clip is reviewed by an ensemble of specialized AI agents before
it can be included in the final movie. This happens in real-time as clips are
generated, not as a post-processing step.

### Agent Roster

```
┌───────────────────────────────────────────────────────────────────┐
│                    CRITIQUE ENSEMBLE                               │
│                                                                    │
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────────────┐ │
│  │ Story Critic │  │ Visual Critic │  │ Continuity Critic      │ │
│  │ (narrative   │  │ (composition, │  │ (character consistency, │ │
│  │  coherence,  │  │  lighting,    │  │  timeline, props,      │ │
│  │  pacing)     │  │  aesthetics)  │  │  setting continuity)   │ │
│  └──────────────┘  └───────────────┘  └────────────────────────┘ │
│                                                                    │
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────────────┐ │
│  │ Audience     │  │ Technical     │  │ Director Critic        │ │
│  │ Critic       │  │ Critic        │  │ (cinematic language,   │ │
│  │ (engagement, │  │ (artifacts,   │  │  shot composition,     │ │
│  │  emotion)    │  │  flicker)     │  │  camera movement)      │ │
│  └──────────────┘  └───────────────┘  └────────────────────────┘ │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                    PRODUCER AGENT                             │ │
│  │  Aggregates all critiques. Decides: approve / revise / cut   │ │
│  └──────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

### Critique Pipeline (per clip)

```
1. STORY CRITIQUE
   ├─ Input: Scene script, shot description, dialog, previous scene context
   ├─ LLM evaluates: Does this shot serve the narrative? Pacing appropriate?
   │  Dialog natural? Emotional arc maintained?
   └─ Output: {score: 0-10, issues: [...], suggestions: [...]}

2. VISUAL CRITIQUE (runs on extracted keyframes)
   ├─ Input: Keyframes from generated clip
   ├─ Vision LLM evaluates: Composition, lighting, color grading, aesthetics
   │  Character appearance matches description?
   └─ Output: {score: 0-10, issues: [...], suggestions: [...]}

3. CONTINUITY CRITIQUE
   ├─ Input: Current clip keyframes + previous clip keyframes + character bible
   ├─ Vision LLM evaluates: Character consistency across clips, setting
   │  consistency, prop placement, lighting continuity, wardrobe
   └─ Output: {score: 0-10, issues: [...], suggestions: [...]}

4. AUDIENCE CRITIQUE
   ├─ Input: Full clip + surrounding context
   ├─ LLM role-plays different audience segments:
   │  General audience, film critic, genre fan, casual viewer
   └─ Output: {engagement: 0-10, emotion_score: 0-10, issues: [...]}

5. TECHNICAL CRITIQUE
   ├─ Input: Raw clip frames + audio
   ├─ Algorithmic checks: Flicker, artifacts, lip-sync, audio levels
   │  Resolution, frame rate, encoding quality
   └─ Output: {score: 0-10, technical_issues: [...]}

6. DIRECTOR CRITIQUE
   ├─ Input: Clip + storyboard + shot list + cinematography notes
   ├─ LLM evaluates: Camera angle appropriate? Movement motivated?
   │  Rule of thirds? Leading lines? Visual storytelling effective?
   └─ Output: {score: 0-10, direction_notes: [...]}

7. PRODUCER DECISION
   ├─ Input: All 6 critique reports
   ├─ Weighted aggregation (configurable weights per genre)
   ├─ Decision logic:
   │   ├─ All scores ≥ 7 → APPROVE
   │   ├─ Any score < 4  → REJECT + regenerate with suggestions
   │   ├─ Otherwise      → REVISE (apply targeted fixes)
   │   └─ Max 3 revision cycles, then best-of-N selection
   └─ Output: {decision: approve|revise|reject, actions: [...]}
```

### Critique at Multiple Levels

Critiques happen at three levels, each with increasing scope:

1. **Shot-level** — Every individual clip (5-15 seconds) is critiqued immediately
   after generation. Fast turnaround. Focus on technical quality and basic
   narrative fit.

2. **Scene-level** — After all shots in a scene are approved, the assembled scene
   is critiqued as a whole. Focus on pacing, continuity, emotional arc within
   the scene.

3. **Movie-level** — After all scenes are assembled, the full movie is critiqued.
   Focus on overall narrative structure, act breaks, character development arcs,
   thematic consistency, runtime pacing.

### LLM Configuration for Critics

All critics use open-weight LLMs. Default configuration:

```yaml
critics:
  text_model: "meta-llama/Llama-3.1-8B-Instruct"  # for text-based critique
  vision_model: "llava-hf/llava-v1.6-mistral-7b"   # for visual critique
  fallback_model: "mistralai/Mistral-7B-Instruct-v0.3"
  max_tokens: 2048
  temperature: 0.3    # lower = more consistent critiques
  num_critics_per_role: 1  # can increase for ensemble voting
  use_different_models_per_critic: true  # diversity of perspective
```

---

## 4. Story Generation Engine (`src/studio/story/`)

Generates original screenplays from text/image prompts using open-weight LLMs.

### Components

- **`writer.py`** — Main story generation. Takes prompt → produces full screenplay
  with act structure, scene breakdowns, dialog, character descriptions.
- **`character_designer.py`** — Generates detailed character bibles from descriptions
  or reference images. Maintains consistency across the movie.
- **`scene_planner.py`** — Breaks screenplay into individual scenes with shot lists,
  camera directions, lighting notes, VFX requirements.
- **`dialog_writer.py`** — Generates natural dialog with character voice consistency.
- **`storyboard.py`** — Generates image prompts for each shot based on scene
  descriptions (text-to-prompt translation for the video generation models).

### Story Generation Pipeline

```
INPUT: User prompt (text and/or image)
  │
  ├─ "A noir detective story set in 2045 Tokyo"
  ├─ [image of a person] → "This person is the lead"
  └─ [image of art style] → "Use this visual style"
  │
  ▼
1. CONCEPT DEVELOPMENT
   ├─ Genre classification
   ├─ Theme extraction
   ├─ World-building outline
   ├─ Tone/mood definition
   └─ Runtime target (default: 20-90 minutes)
   │
   ▼
2. SCREENPLAY GENERATION
   ├─ Three-act structure (or genre-appropriate structure)
   ├─ Character arcs mapped to acts
   ├─ Scene-by-scene outline
   ├─ Full dialog for each scene
   ├─ Action descriptions
   └─ Output: screenplay.yaml (structured format)
   │
   ▼
3. CHARACTER BIBLE
   ├─ For each character:
   │   ├─ Physical description (for image generation prompts)
   │   ├─ Personality traits (for dialog consistency)
   │   ├─ Wardrobe per scene
   │   ├─ Reference images (if provided by user)
   │   └─ LoRA training data requirements
   └─ Output: characters.yaml
   │
   ▼
4. SCENE PLANNING
   ├─ For each scene:
   │   ├─ Shot list with camera directions
   │   ├─ Lighting/mood notes
   │   ├─ Set/location description
   │   ├─ VFX requirements
   │   ├─ Music/sound design notes
   │   └─ Estimated duration
   └─ Output: scenes/*.yaml (compatible with existing pipeline)
   │
   ▼
5. STORYBOARD (prompt engineering)
   ├─ For each shot:
   │   ├─ Positive prompt (optimized for video model)
   │   ├─ Negative prompt
   │   ├─ Reference images/style references
   │   ├─ Camera movement description
   │   └─ Frame count / duration
   └─ Output: shots embedded in scene YAMLs
```

---

## 5. Real Video Generation (`src/studio/models/`)

### Supported Open-Weight Models

**Text-to-Video:**
- CogVideoX-2B (8GB VRAM) — Fast, lower quality
- CogVideoX-5B (20GB VRAM) — Good balance
- Wan2.1-T2V-14B (40GB VRAM) — Highest quality, needs A100
- AnimateDiff + SDXL (12GB) — Style-controllable, shorter clips

**Image-to-Video:**
- CogVideoX-5B-I2V — Animate a keyframe into video
- Stable Video Diffusion (SVD) — High quality, 4-second clips
- Wan2.1-I2V-14B — Best quality, needs A100

**Text-to-Image (keyframes):**
- SDXL 1.0 — Stable, well-understood
- Flux.1 (dev/schnell) — Higher quality, newer
- PixArt-Sigma — Efficient, good quality

**Upscaling:**
- Real-ESRGAN x4 — Frame upscaling
- Video upscaling via temporal-consistent Real-ESRGAN

**Audio:**
- Bark — TTS with emotion/speaker control
- XTTS-v2 — Voice cloning TTS
- MusicGen — Background music generation
- Stable Audio Open — Sound effects

### Generation Strategy

For long-form movies, we cannot generate the entire movie as one continuous video.
Instead, we use a hierarchical approach:

```
MOVIE GENERATION STRATEGY
──────────────────────────
1. Generate keyframes for each shot (text-to-image, SDXL/Flux)
   └─ Critique keyframes → approve/regenerate

2. Animate keyframes into clips (image-to-video, CogVideoX/SVD)
   └─ Critique clips → approve/regenerate

3. Apply character consistency (IP-Adapter / LoRA)
   └─ Train identity LoRA if reference image provided

4. Generate transitions between clips
   └─ Critique transitions → approve/regenerate

5. Upscale all approved clips (Real-ESRGAN)

6. Generate audio per scene:
   ├─ Dialog TTS (Bark/XTTS)
   ├─ Music (MusicGen)
   ├─ Sound effects (Stable Audio)
   └─ Mix and master

7. Assemble final movie (FFmpeg)
   ├─ Scene concatenation with transitions
   ├─ Audio mixing with ducking
   ├─ Subtitle generation
   └─ Final encode (H.264/H.265)
```

---

## 6. Continuous Autonomous Loop (`src/studio/daemon/`)

The daemon runs continuously on the host, managing all autonomous operations.

### Components

- **`daemon.py`** — Main daemon process. Manages lifecycle of all subsystems.
- **`scheduler.py`** — Task scheduler (movie generation, model discovery, critique
  cycles, website updates).
- **`queue.py`** — Priority queue for generation tasks. Supports preemption for
  critique-triggered regeneration.
- **`state.py`** — Persistent state management. Tracks what's in-progress,
  completed, published. Survives restarts.

### Daemon Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                    DAEMON MAIN LOOP                          │
│                                                              │
│  On Start:                                                   │
│  1. Discover GPU resources                                   │
│  2. Load/resume persistent state                             │
│  3. Pull latest models (if scheduled)                        │
│  4. Start subsystem threads:                                 │
│     ├─ GPU Monitor (every 30s)                               │
│     ├─ Model Discovery (daily)                               │
│     ├─ Generation Workers (per GPU)                          │
│     ├─ Critique Workers (dedicated GPU or CPU)               │
│     ├─ Website Updater (on movie completion)                 │
│     └─ Analytics Processor (hourly)                          │
│                                                              │
│  Main Loop (continuous):                                     │
│  1. Check if any movie in progress → continue generation     │
│  2. If no movie in progress:                                 │
│     ├─ Check prompt queue (user-submitted prompts)           │
│     ├─ If empty → generate from story idea pool              │
│     └─ Start new movie pipeline                              │
│  3. Process critique results → trigger regeneration if needed│
│  4. Check if movie complete → run final review               │
│  5. If approved → publish to website                         │
│  6. Log metrics, update state                                │
│  7. Sleep briefly, repeat                                    │
│                                                              │
│  On Shutdown (graceful):                                     │
│  1. Finish current generation step (don't interrupt mid-clip)│
│  2. Save state to disk                                       │
│  3. Release GPU resources                                    │
│  4. Write shutdown log                                       │
└─────────────────────────────────────────────────────────────┘
```

### State Machine (per movie)

```
IDEATION → WRITING → PLANNING → GENERATING → CRITIQUING → REVISING
     ↑                                            │           │
     │                                            ▼           │
     │                                       APPROVED ────────┘
     │                                            │
     │                                            ▼
     │                                    POST_PRODUCTION
     │                                            │
     │                                            ▼
     └─────── NEXT MOVIE ◀──────────── PUBLISHED
```

---

## 7. Website / Distribution (`website/`)

Netflix-like streaming website for publishing and watching generated movies.

### Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS
- **Video Player**: Video.js or Plyr (HLS streaming)
- **Database**: SQLite (single host) → PostgreSQL (scale)
- **API**: Next.js API routes → talks to Movilizer daemon
- **Storage**: Local filesystem (with optional S3/MinIO)

### Pages

```
/                    — Homepage (featured movies, new releases, trending)
/browse              — Browse all movies (filter by genre, rating, date)
/movie/[id]          — Movie detail page (poster, synopsis, play button)
/movie/[id]/watch    — Full-screen video player with HLS streaming
/stats               — Platform analytics (total movies, views, etc.)
/api/movies          — REST API for movie data
/api/movies/[id]     — Single movie data
/api/analytics       — Analytics ingestion endpoint
```

### Movie Metadata Schema

```yaml
movie:
  id: "mov_001"
  title: "Neon Shadows"
  tagline: "In 2045 Tokyo, truth hides in the light"
  synopsis: "..."
  genre: ["noir", "sci-fi"]
  duration_minutes: 45
  resolution: "1920x1080"
  poster_url: "/media/mov_001/poster.jpg"
  trailer_url: "/media/mov_001/trailer.mp4"
  video_url: "/media/mov_001/movie.mp4"
  hls_url: "/media/mov_001/stream/index.m3u8"
  subtitles_url: "/media/mov_001/subs.srt"
  created_at: "2026-03-12T10:00:00Z"
  published_at: "2026-03-12T12:00:00Z"
  generation_info:
    models_used: ["CogVideoX-5B", "SDXL", "Llama-3.1-8B"]
    total_generation_time_hours: 48
    total_clips_generated: 340
    clips_approved: 120
    revision_cycles: 2.4  # average per clip
    critic_scores:
      story: 8.2
      visual: 7.8
      continuity: 8.5
      audience: 7.5
      technical: 9.1
      direction: 7.9
  analytics:
    views: 0
    completions: 0
    avg_watch_time_minutes: 0
    likes: 0
    dislikes: 0
```

### Analytics-Driven Content Improvement

The website tracks viewer behavior, which feeds back into story generation:

```
ANALYTICS FEEDBACK LOOP
────────────────────────
1. Track per-movie:
   ├─ View count
   ├─ Completion rate (% who finish the movie)
   ├─ Drop-off points (where viewers stop watching)
   ├─ Rewatch segments (parts viewers replay)
   ├─ Likes / dislikes
   └─ Time-of-day viewing patterns

2. Aggregate insights:
   ├─ Best-performing genres
   ├─ Optimal movie length
   ├─ Engagement patterns (action scenes vs. dialog)
   ├─ Character types that resonate
   └─ Visual styles preferred

3. Feed into story generation:
   ├─ Bias prompt pool toward popular genres
   ├─ Adjust target runtime to optimal length
   ├─ Emphasize scene types with high engagement
   ├─ Evolve visual style toward preferred aesthetics
   └─ Weight critic scores by viewer correlation
```

---

## 8. Directory Structure (New + Existing)

```
src/studio/
├── (existing modules — unchanged)
│
├── gpu/                    # NEW: GPU resource management
│   ├── __init__.py
│   ├── discovery.py        # GPU detection and enumeration
│   ├── allocator.py        # Model-to-GPU assignment
│   └── monitor.py          # Utilization tracking
│
├── discovery/              # NEW: Model auto-discovery
│   ├── __init__.py
│   ├── scanner.py          # HuggingFace model scanning
│   ├── benchmark.py        # Model benchmarking
│   ├── integrator.py       # Model integration/promotion
│   └── scheduler.py        # Discovery scheduling
│
├── critics/                # NEW: Multi-agent critique
│   ├── __init__.py
│   ├── base.py             # Critic base class and protocols
│   ├── story_critic.py     # Narrative/dialog critique
│   ├── visual_critic.py    # Composition/aesthetics critique
│   ├── continuity_critic.py # Cross-clip consistency
│   ├── audience_critic.py  # Engagement/emotion prediction
│   ├── technical_critic.py # Artifacts/quality checks
│   ├── director_critic.py  # Cinematic language critique
│   ├── producer.py         # Final decision aggregator
│   ├── ensemble.py         # Ensemble runner / voting
│   └── llm_pool.py         # Manages local LLM instances
│
├── story/                  # NEW: Story generation
│   ├── __init__.py
│   ├── writer.py           # Screenplay generation
│   ├── character_designer.py # Character bible creation
│   ├── scene_planner.py    # Scene/shot breakdown
│   ├── dialog_writer.py    # Dialog generation
│   └── storyboard.py       # Shot-to-prompt translation
│
├── daemon/                 # NEW: Continuous operation
│   ├── __init__.py
│   ├── daemon.py           # Main daemon process
│   ├── scheduler.py        # Task scheduling
│   ├── queue.py            # Priority task queue
│   └── state.py            # Persistent state management
│
├── models/                 # EXTENDED
│   ├── (existing files)
│   ├── video_gen.py        # NEW: CogVideoX / Wan2.1 integration
│   ├── image_gen.py        # NEW: SDXL / Flux real generation
│   ├── tts_gen.py          # NEW: Bark / XTTS integration
│   ├── music_gen.py        # NEW: MusicGen integration
│   └── upscale.py          # NEW: Real-ESRGAN integration
│
└── website/                # NEW: Distribution
    ├── __init__.py
    ├── publisher.py         # Movie publishing pipeline
    ├── analytics.py         # Analytics processing
    └── api.py               # Website data API

website/                     # NEW: Next.js frontend (top-level)
├── package.json
├── next.config.js
├── tailwind.config.js
├── app/
│   ├── layout.tsx
│   ├── page.tsx             # Homepage
│   ├── browse/page.tsx      # Browse movies
│   ├── movie/[id]/
│   │   ├── page.tsx         # Movie detail
│   │   └── watch/page.tsx   # Video player
│   ├── stats/page.tsx       # Analytics dashboard
│   └── api/
│       ├── movies/route.ts
│       └── analytics/route.ts
├── components/
│   ├── MovieCard.tsx
│   ├── VideoPlayer.tsx
│   ├── MovieGrid.tsx
│   └── Navbar.tsx
└── public/
    └── media/               # Generated movie files served here
```

---

## 9. Configuration

### Master Daemon Config (`configs/daemon/default.yaml`)

```yaml
daemon:
  mode: continuous           # continuous | single_movie | manual
  state_file: "state/daemon_state.json"
  log_level: INFO

  generation:
    max_concurrent_movies: 1
    target_runtime_minutes: 30
    max_revision_cycles: 5
    min_quality_threshold: 7.0  # producer approval threshold (0-10)
    prompt_source: auto         # auto | queue | manual

  gpu:
    poll_interval_sec: 30
    min_free_vram_mb: 2048
    allow_multi_gpu: true
    prefer_llm_gpu: true

  models:
    video: "THUDM/CogVideoX-5b"
    video_i2v: "THUDM/CogVideoX-5b-I2V"
    image: "stabilityai/stable-diffusion-xl-base-1.0"
    llm: "meta-llama/Llama-3.1-8B-Instruct"
    vision_llm: "llava-hf/llava-v1.6-mistral-7b-hf"
    tts: "suno/bark"
    music: "facebook/musicgen-medium"
    upscale: "ai-forever/Real-ESRGAN"

  discovery:
    enabled: true
    scan_interval_hours: 24
    benchmark_interval_hours: 168  # weekly
    auto_integrate: false          # require manual approval
    hf_tasks:
      - "text-to-video"
      - "text-to-image"
      - "text-generation"
      - "text-to-speech"
      - "text-to-audio"

  critics:
    enabled: true
    approval_threshold: 7.0
    max_revisions: 3
    weights:
      story: 0.20
      visual: 0.20
      continuity: 0.20
      audience: 0.15
      technical: 0.15
      direction: 0.10

  website:
    enabled: true
    port: 3000
    media_dir: "website/public/media"
    auto_publish: true
    hls_enabled: true
```

---

## 10. Dependencies

### Python (additions to pyproject.toml)

```toml
[project.optional-dependencies]
gpu = ["pynvml>=11.5", "GPUtil>=1.4"]
video_gen = ["diffusers>=0.27", "accelerate>=0.27", "transformers>=4.38", "torch>=2.1"]
audio_gen = ["bark>=0.1", "TTS>=0.22", "audiocraft>=1.2"]
upscale = ["realesrgan>=0.3"]
llm = ["vllm>=0.4", "transformers>=4.38"]
website = ["fastapi>=0.115", "uvicorn>=0.30", "aiofiles>=23.2"]
full = ["movilizer-studio[gpu,video_gen,audio_gen,upscale,llm,website]"]
```

### Node.js (website/package.json)

```json
{
  "dependencies": {
    "next": "^14",
    "react": "^18",
    "tailwindcss": "^3",
    "video.js": "^8",
    "@videojs/http-streaming": "^3"
  }
}
```

---

## 11. Running the System

### Quick Start

```bash
# Install everything
pip install -e ".[full]" --break-system-packages
cd website && npm install && cd ..

# Start the daemon (runs everything)
python -m studio.daemon --config configs/daemon/default.yaml

# Or start components individually:
python -m studio.daemon --mode single_movie --prompt "A noir detective story in 2045 Tokyo"
python -m studio.server --config configs/server/default.yaml
cd website && npm run dev
```

### Docker (future)

```bash
docker compose up  # Starts daemon + website + monitoring
```
