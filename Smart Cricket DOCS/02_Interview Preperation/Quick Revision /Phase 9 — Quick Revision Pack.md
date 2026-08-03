# Phase 9 — Quick Revision Pack

# Question 1: What was the goal of Phase 9 in Smart Cricket?

## Quick Answer

Phase 9 added shot segmentation and prediction gating.

Goal:

```text
one batting motion → one completed segment → one final prediction trigger
```

It does not retrain the classifier. It decides when the classifier should be called.

---

# Question 2: Why is frame-by-frame prediction a problem?

## Quick Answer

One swing can create unstable intermediate predictions.

Example:

```text
cover_drive → defensive_shot → pull_shot
```

The correct user-facing behavior is:

```text
one completed shot → one prediction
```

---

# Question 3: What motion signals does Phase 9 use?

## Quick Answer

It uses existing temporal features:

- wrist velocities
- elbow velocities
- body center velocity
- lead wrist acceleration proxy
- frame motion energy

This keeps segmentation aligned with the validated `[T, 32]` feature contract.

---

# Question 4: Why use a state machine?

## Quick Answer

A state machine makes segmentation explainable.

Roadmap states:

```text
idle → preparation → backswing → swing → follow_through → completed → cooldown
```

It is easier to debug than a premature learned segmentation model.

---

# Question 5: What is cooldown logic and why is it important?

## Quick Answer

Cooldown prevents duplicate triggers after one shot.

Follow-through still contains motion, so without cooldown the system may detect the same shot twice.

Cooldown improves real-time stability.

---

# Question 6: What did Phase 9 validation prove?

## Quick Answer

Validation ran on:

```text
X_sequence.npy = (80, 60, 32)
```

Results:

```text
segments detected = 80/80
single-trigger sequences = 80/80
validation passed = True
```

65 clips completed at sequence end, which is reported honestly.

---

# Question 7: Did Phase 9 change the trained classifier?

## Quick Answer

No.

Phase 8 trained the classifier. Phase 9 only adds segmentation and trigger control.

The best model checkpoint remains unchanged:

```text
ml/artifacts/phase8/best_model/checkpoint.pt
```

---

# Question 8: What future phases depend on Phase 9?

## Quick Answer

Phase 10 scoring, Phase 11 feedback, and Phase 12 inference depend on stable shot segmentation.

Segmentation turns continuous motion into one usable shot event.

Without it, later scoring and feedback would be unstable.
