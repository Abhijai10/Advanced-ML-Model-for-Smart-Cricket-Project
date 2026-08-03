# Phase 9 Interview Preparation Pack — Shot Segmentation

# Section 1 — Deep Interview Pack

# Question 1: What was the goal of Phase 9 in Smart Cricket?

## Short Answer

Phase 9 added shot segmentation and prediction gating so one batting motion produces one final prediction trigger.

## Deep Technical Explanation

After Phase 8, Smart Cricket had a trained temporal classifier. But a classifier alone does not decide when to predict. If used naively on every frame or partial window, it may output multiple labels during one swing.

Phase 9 solves that control problem:

```text
temporal motion sequence → detected shot segment → one final prediction trigger
```

It creates the event boundary around one complete batting motion.

## Engineering Reasoning

Real ML applications need timing logic. A model can be technically correct but operationally unstable if it fires repeatedly during one action.

## Why This Decision Was Taken

The locked roadmap states that prediction should happen after the complete motion is observed, not continuously per frame.

## Tradeoffs / Risks / Limitations

The current implementation is threshold/state-machine based. It is explainable and appropriate for the current dataset, but live-stream behavior still needs later validation.

## Important Engineering Insight

Segmentation answers:

```text
when should prediction happen?
```

Classification answers:

```text
what shot is this?
```

They are related but not the same problem.

---

# Question 2: Why is frame-by-frame prediction a problem?

## Short Answer

Because one swing can produce many unstable intermediate predictions before the motion is complete.

## Deep Technical Explanation

A cricket shot unfolds over time:

```text
stance → backswing → swing → follow-through
```

Early frames may not contain enough evidence. During a swing, the model might see partial movement and alternate between labels.

That creates outputs like:

```text
cover_drive → defensive_shot → pull_shot → cover_drive
```

For the user, this feels unstable. The correct behavior is:

```text
one completed shot → one prediction
```

## Engineering Reasoning

The app should expose stable shot events, not raw model noise.

## Why This Decision Was Taken

Smart Cricket is intended to become a coaching system. Coaching feedback must be based on one completed action, not many partial guesses.

## Tradeoffs / Risks / Limitations

Waiting until completion introduces some latency, but it improves correctness and user trust.

## Important Engineering Insight

In real-time ML, timing can be as important as model accuracy.

---

# Question 3: What motion signals does Phase 9 use?

## Short Answer

It uses existing temporal features such as wrist velocity, elbow velocity, body center velocity, lead wrist acceleration proxy, and frame motion energy.

## Deep Technical Explanation

Phase 9 does not return to raw video. It consumes the validated `[T, 32]` temporal feature representation.

The motion-energy signal combines:

- lead wrist velocity
- trail wrist velocity
- lead/trail elbow velocity
- body center velocity
- lead wrist acceleration proxy
- frame motion energy

These features are already aligned with the cricket motion representation created earlier.

## Engineering Reasoning

Using existing temporal features keeps the pipeline consistent and avoids adding a second unvalidated representation.

## Why This Decision Was Taken

The roadmap prioritizes explainability and motion thresholds before advanced segmentation models.

## Tradeoffs / Risks / Limitations

The signal depends on engineered features. If the features are noisy, segmentation can also become noisy.

## Important Engineering Insight

Segmentation should reuse validated upstream representations when possible.

---

# Question 4: Why use a state machine?

## Short Answer

A state machine makes shot progress explainable, debuggable, and controlled.

## Deep Technical Explanation

Phase 9 uses the roadmap state path:

```text
idle → preparation → backswing → swing → follow_through → completed → cooldown
```

Each frame has a state. This allows the system to explain why a prediction trigger did or did not happen.

## Engineering Reasoning

State machines are excellent for event detection when transitions are rule-based and must be inspected.

## Why This Decision Was Taken

The dataset is small and segmentation labels are not available. A learned model would be premature.

## Tradeoffs / Risks / Limitations

Thresholds may need tuning for new camera angles or live streams.

## Important Engineering Insight

A simple state machine can be more production-useful than a premature black-box model.

---

# Question 5: What is cooldown logic and why is it important?

## Short Answer

Cooldown suppresses new triggers immediately after one completed shot so the same motion is not counted twice.

## Deep Technical Explanation

After a prediction trigger, the body may still be moving during follow-through. Without cooldown, the system could mistake this residual motion as a new shot.

Cooldown creates a short ignore period after completion.

## Engineering Reasoning

This is common in real-time event systems: once an event fires, prevent duplicate detections until the system returns to a stable state.

## Why This Decision Was Taken

The roadmap explicitly requires cooldown logic to reduce repeated predictions.

## Tradeoffs / Risks / Limitations

If cooldown is too long, a very quick second shot could be delayed. If it is too short, duplicate triggers can occur.

## Important Engineering Insight

Cooldown is not an ML trick. It is production control logic that makes ML outputs usable.

---

# Question 6: What did Phase 9 validation prove?

## Short Answer

It proved that all 80 finalized temporal clips produce one detected segment and exactly one prediction trigger.

## Deep Technical Explanation

The validation script ran over:

```text
X_sequence.npy = (80, 60, 32)
```

Results:

```text
Segments detected: 80 / 80
Single-trigger sequences: 80 / 80
Validation passed: True
```

The validator also writes a state trace so transitions can be inspected.

## Engineering Reasoning

This confirms the segmenter works on the official completed temporal dataset without modifying model or dataset artifacts.

## Why This Decision Was Taken

Phase 9 needed to prove behavior end-to-end, not only provide code.

## Tradeoffs / Risks / Limitations

65 sequences completed at sequence end, meaning many finalized clips remain motion-active until frame 59. This is acceptable for clipped sequences but live streams need stronger stabilization validation later.

## Important Engineering Insight

Validation should report limitations, not hide them.

---

# Question 7: Did Phase 9 change the trained classifier?

## Short Answer

No. Phase 9 did not retrain or modify the Phase 8 model.

## Deep Technical Explanation

Phase 8 selected the best classifier checkpoint. Phase 9 only creates a gating layer that determines when a completed shot is ready for prediction.

The Phase 8 checkpoint remains:

```text
ml/artifacts/phase8/best_model/checkpoint.pt
```

## Engineering Reasoning

Changing model weights during segmentation would mix phase boundaries and make evaluation hard to trust.

## Why This Decision Was Taken

The roadmap separates model training from segmentation.

## Tradeoffs / Risks / Limitations

The segmenter currently validates trigger behavior, not live model inference.

## Important Engineering Insight

Preserve phase boundaries so each system component can be debugged independently.

---

# Question 8: What future phases depend on Phase 9?

## Short Answer

Technique scoring, feedback, and inference all depend on stable shot segmentation.

## Deep Technical Explanation

Phase 10 technique scoring should compare a completed shot segment, not random partial frames.

Phase 11 feedback should explain one stable action.

Phase 12 inference needs segmentation so real-time prediction does not fire continuously.

## Engineering Reasoning

Segmentation turns a stream into an event. Later systems operate on that event.

## Why This Decision Was Taken

Without segmentation, final app behavior would be unstable and unprofessional.

## Tradeoffs / Risks / Limitations

The current implementation is a foundation. Live deployment will need buffering, latency, and camera-angle robustness checks.

## Important Engineering Insight

Segmentation is the bridge between model intelligence and usable product behavior.
