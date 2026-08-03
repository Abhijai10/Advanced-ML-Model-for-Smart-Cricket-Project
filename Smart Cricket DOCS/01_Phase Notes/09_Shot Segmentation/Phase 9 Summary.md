# Phase 9 — Shot Segmentation

# 🎯 Goal of the Phase

Phase 9 adds the shot segmentation and prediction-gating layer for Smart Cricket.

The core problem solved in this phase is:

```text
one batting motion should produce one final prediction
```

Without segmentation, a future live system could classify continuously during the same swing and produce unstable repeated outputs:

```text
cover_drive → defensive_shot → cover_drive → pull_shot
```

That would feel unprofessional and confusing.

Phase 9 transforms:

```text
temporal pose-feature sequence
→ motion-energy signal
→ explainable state machine
→ detected shot segment
→ one prediction trigger
```

This phase does not retrain the Phase 8 classifier. It creates the control layer that decides when a completed motion is ready for one final prediction.

# 🧠 Core Concepts Introduced

## Shot Segmentation

Shot segmentation means identifying the meaningful start and end of a batting action.

In Smart Cricket, the finalized training clips already contain one labeled shot, but the future real-time system will receive a stream. A stream needs event boundaries:

```text
idle movement
→ preparation
→ swing
→ follow-through
→ completed shot
```

Segmentation protects the classifier from being called at every frame.

## Motion Energy

Motion energy is a compact signal that estimates how much cricket-relevant body movement is happening at each frame.

Phase 9 computes this from the existing 32 temporal features, including:

- lead wrist velocity
- trail wrist velocity
- elbow velocities
- body center velocity
- lead wrist acceleration proxy
- frame motion energy

This preserves roadmap continuity because Phase 9 uses the already validated temporal feature contract instead of inventing new raw-pixel logic.

## Temporal Smoothing

Raw motion values can jump frame to frame. Phase 9 applies a moving average so state transitions are less sensitive to tiny fluctuations.

The goal is not to hide important motion, but to avoid unstable state changes caused by noisy single frames.

## State Machine

The segmentation state machine follows the locked roadmap:

```text
idle
→ preparation
→ backswing
→ swing
→ follow_through
→ completed
→ cooldown
```

Each state is explainable. This is important because segmentation will eventually affect user-visible predictions.

## Cooldown

Cooldown prevents repeated prediction triggers after one completed shot. Once a trigger fires, the system ignores immediate follow-up movement for a short period.

This is a practical real-time engineering pattern: after detecting one event, do not instantly re-detect the same event.

# 🏗️ System-Level Importance

Phase 9 sits between model training and future inference.

Phase 8 answered:

```text
Can the temporal classifier learn shot classes?
```

Phase 9 answers:

```text
When should the system call that classifier?
```

This distinction matters. A trained classifier alone is not enough for a stable app. A real application needs a gating layer so the model produces one prediction per completed motion.

Downstream phases depend on this:

- Phase 10 technique scoring should score a completed shot segment, not random frames.
- Phase 11 feedback should use one stable prediction and one motion segment.
- Phase 12 inference should use segmentation before final prediction.

# 📂 Important Files / Scripts

## `ml/src/segmentation/motion_energy.py`

Computes the per-frame motion-energy signal from the official 32-D temporal feature sequence.

Important responsibilities:

- validate `[T, 32]` input
- combine relevant motion features
- normalize motion energy robustly
- smooth frame-level energy
- expose thresholds for the state machine

## `ml/src/segmentation/state_machine.py`

Implements the explainable shot-progress state machine.

Important responsibilities:

- track current shot state
- detect transition from idle into motion
- detect follow-through/completion
- emit at most one prediction trigger
- enforce cooldown behavior
- produce frame-level trace rows for debugging

## `ml/src/segmentation/shot_segmenter.py`

Combines motion energy and the state machine into a usable segmenter.

Input:

```text
one temporal feature sequence [T, 32]
```

Output:

```text
ShotSegment(start_frame, end_frame, peak_frame, prediction_trigger_frame)
```

## `ml/src/segmentation/validate_shot_segmentation.py`

Runs Phase 9 validation over the official finalized temporal dataset.

Outputs:

- `ml/artifacts/phase9/segmentation_debug_report.md`
- `ml/artifacts/phase9/segmentation_health.json`
- `ml/artifacts/phase9/segmentation_segments.csv`
- `ml/artifacts/phase9/segmentation_state_trace.csv`

## `ml/src/segmentation/tests/`

Focused tests for:

- motion-energy computation
- input validation
- state transitions
- cooldown behavior
- one-shot trigger behavior

# 🔄 Data Flow

```text
X_sequence.npy
→ one [60, 32] sequence
→ motion-energy extraction
→ smoothing
→ state machine
→ completed segment
→ one prediction trigger
→ debug artifacts
```

Validation result:

```text
Input: (80, 60, 32)
Segments detected: 80 / 80
Single-trigger sequences: 80 / 80
Sequence-end completions: 65
Validation passed: True
```

# ⚠️ Common Mistakes / Pitfalls

## Mistake 1: Classifying Every Frame

A frame-by-frame classifier can produce repeated or contradictory predictions during one swing. Phase 9 prevents this by gating prediction until a motion segment is completed.

## Mistake 2: Making Segmentation a Black Box Too Early

A learned segmentation model would require labels and more data. Phase 9 intentionally uses explainable thresholds and a state machine first.

## Mistake 3: Ignoring Cooldown

Without cooldown, follow-through motion can be mistaken as a new shot.

## Mistake 4: Overclaiming Live Readiness

The current validation uses finalized 60-frame clips. Live streams will need separate buffering, latency, and stabilization validation.

# 💡 Key Engineering Decisions

## Use Existing Temporal Features

The segmenter uses the Phase 5.5/6 temporal feature schema instead of raw video pixels. This keeps the system explainable and consistent.

## Use State Machine Before Learned Segmentation

The roadmap explicitly prefers motion thresholds before advanced segmentation models. This is appropriate because the dataset is small and segmentation labels do not yet exist.

## Emit Debug Artifacts

Segmentation failures are hard to reason about without traces. Phase 9 writes per-frame state traces and per-sequence segment summaries.

## Allow Sequence-End Completion for Finalized Clips

The current dataset clips already contain one shot. Many clips remain motion-active through frame 59, so Phase 9 allows sequence-end completion and reports it explicitly.

# 📘 What I Should Write in Notes

- Segmentation is not classification; it decides when classification should happen.
- Motion energy is an event-detection signal, not a shot label.
- State machines are useful when behavior must be explainable and debuggable.
- Cooldown is essential in real-time event detection.
- Phase 9 prepares inference stability without implementing the full inference pipeline.

# 🧠 Personal Learning Insights

Phase 9 shows that production ML systems need control logic around models.

A model can be accurate but still unpleasant to use if predictions fire at the wrong time.

The big engineering lesson:

```text
Good ML systems are not only about prediction quality.
They are also about timing, gating, stability, and user experience.
```

# 🚀 Future Impact

Phase 9 prepares:

- Phase 10 technique scoring, because scoring needs a completed shot segment
- Phase 11 feedback, because feedback needs one stable shot event
- Phase 12 inference, because live prediction must be gated
- future real-time app behavior, because repeated predictions would feel unstable
