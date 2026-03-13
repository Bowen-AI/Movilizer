# Multi-Agent Critique System

The Movilizer Multi-Agent Critique System provides comprehensive AI-based evaluation of generated video clips using multiple specialized critics that assess different aspects of quality.

## Architecture Overview

```
Generated Clip
     ↓
    [EnsembleRunner]
     ↓
  ┌─┴─────────────────────────────────────────┐
  ↓       ↓       ↓       ↓       ↓       ↓
[Story] [Visual] [Technical] [Director] [Audience] [Continuity]
  ↓       ↓       ↓       ↓       ↓       ↓
  └─┬─────────────────────────────────────────┘
    ↓
[ProducerAgent]
    ↓
 Decision: APPROVE / REVISE / REJECT
    ↓
 Revision Instructions (if needed)
```

## Core Components

### Base Classes (`base.py`)

- **CritiqueLevel**: Enum for critique scope (SHOT, SCENE, MOVIE)
- **ProducerDecision**: Enum for producer's decision (APPROVE, REVISE, REJECT)
- **CritiqueResult**: Dataclass containing:
  - `score`: 0-10 rating
  - `issues`: List of problems found
  - `suggestions`: List of improvement recommendations
  - `reasoning`: Explanation of the score
  - `metadata`: Additional data
- **CriticBase**: Abstract base class for all critics
  - Implements async `evaluate()` method
  - Provides helper method `_create_result()`
- **CritiqueContext**: Contains all information about the clip being evaluated

### Critics

Each critic specializes in a different aspect of quality:

#### StoryCritic
- Evaluates narrative coherence, pacing, dialogue, emotional arc
- Uses LLM with story analysis prompt
- Parses structured JSON responses from LLM
- Falls back to text parsing if JSON unavailable

#### VisualCritic
- Evaluates composition, lighting, color, aesthetics
- Uses vision LLM (LLaVA) if available
- Falls back to OpenCV-based heuristic analysis
- Checks for extreme brightness changes, resolution mismatches

#### ContinuityCritic
- Compares current clip with previous clips in scene
- Checks character appearance, props, lighting, wardrobe
- Uses vision LLM or pixel-level comparison
- Detects brightness and color discontinuities

#### AudienceCritic
- Role-plays different audience segments
- Simulates reactions from: general, critic, genre_fan, casual perspectives
- Predicts engagement and emotional response
- Aggregates results across personas

#### TechnicalCritic
- Algorithmic quality checks (no LLM needed)
- Detects flicker between frames
- Identifies compression artifacts
- Checks resolution, file integrity, frame rate
- Analyzes audio quality if present

#### DirectorCritic
- Evaluates cinematographic language and directorial choices
- Assesses composition (rule of thirds, leading lines, framing)
- Analyzes camera angles and visual storytelling
- Uses vision LLM + heuristic composition analysis

### LLM Pool (`llm_pool.py`)

Manages local open-weight model instances with graceful fallbacks:

```
[LLMPool]
    ↓
  vLLM (preferred)
    ↓ (if unavailable)
  Transformers
    ↓ (if unavailable)
  Mock Responses (for testing)
```

**Features:**
- Loads multiple models simultaneously on different GPUs
- Async generate() method with configurable parameters
- Graceful degradation: fails over to next backend
- Mock mode for testing without actual models
- Proper resource cleanup

### Producer Agent (`producer.py`)

Aggregates critique results and makes generation decisions:

**Configuration (ProducerConfig):**
- Approval threshold: >= 7.0 → APPROVE
- Critical threshold: < 4.0 → REJECT
- Weighted scoring per critic (customizable)
- Genre-specific weights
- Maximum revision cycles (default: 3)
- Required critics that must pass
- Veto critics that can reject

**Decision Logic:**
1. Check veto conditions (hard failures)
2. Check required critics
3. If score >= approval_threshold → APPROVE
4. If any score < critical_threshold → REJECT
5. Otherwise → REVISE (with instructions)
6. After max revisions → force APPROVE

**Output (ProducerDecision_Result):**
- Decision (APPROVE/REVISE/REJECT)
- Overall weighted score
- Per-critic scores
- Detailed reasoning
- Revision instructions
- Revision count

### Ensemble Runner (`ensemble.py`)

Orchestrates running all critics:

**Features:**
- Parallel execution of critics (asyncio)
- Sequential fallback if needed
- Lazy critic initialization
- Shared LLM pool for efficiency
- Clean shutdown of resources
- Comprehensive result aggregation

## Usage Examples

### Basic Critique

```python
import asyncio
from pathlib import Path
from src.studio.critics import (
    EnsembleRunner,
    EnsembleConfig,
    CritiqueContext,
)

async def critique_clip():
    # Create critique context
    context = CritiqueContext(
        run_id="run_001",
        project="movie_project",
        scene="scene_1",
        shot="shot_001",
        shot_dir=Path("outputs/shot_001"),
        frames=[Path("frame_0000.png"), Path("frame_0001.png")],
        clip_path=Path("output.mp4"),
        script="Actor delivers emotional dialogue",
        shot_description="Close-up of actor with tears",
        genre="drama",
        tone="sad, contemplative",
    )

    # Run ensemble critique
    config = EnsembleConfig(
        critics=["story", "visual", "technical", "director", "audience"],
        parallel=True,
        use_mock_llm=True,  # For testing without models
    )

    runner = EnsembleRunner(config=config)
    try:
        result = await runner.run(context)

        print(f"Producer Decision: {result['producer_decision'].decision.value}")
        print(f"Overall Score: {result['producer_decision'].overall_score:.1f}")

        for critic_name, score in result['producer_decision'].critic_scores.items():
            print(f"  {critic_name}: {score:.1f}")

        if result['producer_decision'].revision_instructions:
            print("Revision Instructions:")
            for instruction in result['producer_decision'].revision_instructions:
                print(f"  - {instruction}")
    finally:
        await runner.shutdown()

asyncio.run(critique_clip())
```

### Convenience Function

```python
from src.studio.critics import run_ensemble_critique, EnsembleConfig

result = await run_ensemble_critique(context, config)
```

### Custom Critic

```python
from src.studio.critics import CriticBase, CritiqueContext, CritiqueLevel

class CustomCritic(CriticBase):
    def __init__(self):
        super().__init__("CustomCritic", CritiqueLevel.SHOT)

    async def evaluate(self, context: CritiqueContext):
        # Your evaluation logic
        score = 8.0
        issues = []
        suggestions = []

        return self._create_result(
            score=score,
            issues=issues,
            suggestions=suggestions,
            reasoning="Custom analysis"
        )
```

## Configuration

See `configs/critics/default.yaml` for comprehensive configuration options:

- **Ensemble settings**: Which critics to run, parallelization
- **Producer thresholds**: Approval, critical, revision points
- **Critic weights**: Per-critic importance (genre-specific)
- **LLM settings**: Model selection, backend preferences
- **Critic-specific config**: Temperature, heuristic fallbacks, etc.

## Score Interpretation

- **9-10**: Excellent quality, ready to ship
- **7-9**: Good quality, minor improvements possible
- **5-7**: Acceptable, consider revisions
- **4-5**: Notable issues, revisions recommended
- **0-4**: Critical problems, rejection likely

## Performance Considerations

### Parallel Execution
- Running all 6 critics in parallel: ~10-30s per clip (with LLM)
- Sequential: ~30-90s per clip
- Technical critic (no LLM): <1s

### Memory Usage
- Each loaded LLM: 4-16GB (depending on model)
- LLMPool manages loading/unloading
- Mock mode: minimal memory

### Fallback Strategy
- Visual critic: LLM → OpenCV heuristics → generic feedback
- Continuity critic: Vision LLM → pixel comparison → generic feedback
- All critics: graceful degradation with mock responses

## Extending the System

### Adding a New Critic

1. Create `new_critic.py` in `src/studio/critics/`
2. Subclass `CriticBase`
3. Implement async `evaluate(context)` method
4. Register in `EnsembleRunner._create_critic()`
5. Add to ensemble config

### Customizing Producer Logic

Modify `ProducerConfig` for different decision thresholds:

```python
config = ProducerConfig(
    approval_threshold=8.0,  # Higher standard
    max_revisions=5,
    critic_weights={
        "story": 1.5,
        "visual": 1.2,
        "technical": 1.0,
    },
    genre_weights={
        "horror": {
            "visual": 1.5,  # Visuals extra important for horror
            "audience": 1.3,
        }
    },
    veto_critics={
        "technical": 2.0,  # Hard fail on technical issues
    }
)

producer = ProducerAgent(config)
```

## Testing

All critics include mock/fallback modes for testing without models:

```python
config = EnsembleConfig(use_mock_llm=True)
runner = EnsembleRunner(config=config)
```

This allows testing the entire system without GPU/model requirements.

## Integration with Pipeline

Example integration with Movilizer's generation pipeline:

```python
# After generating a clip
result = await run_ensemble_critique(context, config)

if result['producer_decision'].decision == ProducerDecision.APPROVE:
    save_to_final_output(clip)
elif result['producer_decision'].decision == ProducerDecision.REVISE:
    # Regenerate with revision instructions
    new_context = update_prompt_with_instructions(context, result)
    regenerate_clip(new_context)
else:  # REJECT
    log_failure_and_skip(clip)
```

## File Structure

```
src/studio/critics/
├── __init__.py              # Package exports
├── base.py                  # Base classes and enums
├── llm_pool.py              # LLM management
├── story_critic.py          # Narrative critique
├── visual_critic.py         # Visual composition
├── continuity_critic.py     # Scene continuity
├── audience_critic.py       # Audience simulation
├── technical_critic.py      # Technical quality
├── director_critic.py       # Cinematography
├── producer.py              # Decision aggregation
└── ensemble.py              # Orchestration

configs/critics/
└── default.yaml             # Configuration
```

## Future Enhancements

- [ ] Integrate with actual vision LLMs (LLaVA, Claude Vision)
- [ ] Add audio-specific critic (speech quality, music, effects)
- [ ] Character consistency tracking across scenes
- [ ] Historical scoring for learning critic calibration
- [ ] Web UI for reviewing critique results
- [ ] Feedback loop to improve critic prompts
- [ ] Integration with external critic APIs
- [ ] Movie-level aggregate scoring
