# Phase 12 — Offline Inference Pipeline

# 🎯 Goal of the Phase

Phase 12 connected the completed Smart Cricket ML modules into one offline analysis pipeline.

Before this phase, the system had separate working subsystems:

```text
trained classifier
shot segmentation
technique scoring
feedback generation
```

Phase 12 orchestrates them into:

```text
one stable JSON result
```

The v1 input is a finalized temporal feature sequence shaped:

```text
[60, 32]
```

The output contains:

```text
predicted_shot
shot_confidence
technique_match_score
detected_issues
coaching_tips
detailed_feedback
spoken_feedback
debug_metadata
```

# 🧠 Core Concepts Introduced

## Pipeline Orchestration

Phase 12 is not about inventing new ML logic. It is about connecting validated modules in the correct order.

The pipeline runs:

```text
sequence validation
→ model prediction
→ shot segmentation
→ technique scoring
→ feedback generation
→ result schema serialization
```

## Stable Result Schema

The result schema is important because Phase 13 API integration should return a stable JSON response. The API should not invent its own response shape or duplicate ML logic.

## Offline Before API

The system now has an offline inference function before adding web/API transport. This keeps business logic separate from backend routing.

## Debug Metadata

The output includes debug metadata for:

- pipeline version
- model artifact path
- template artifact path
- segmentation completion
- feedback source
- input contract

This makes future API failures easier to diagnose.

# 🏗️ System-Level Importance

Phase 12 turns Smart Cricket from separate ML modules into an integrated analysis system.

The architecture now flows as:

```text
temporal sequence
→ selected Phase 8 model
→ Phase 9 segmenter
→ Phase 10 scorer
→ Phase 11 feedback engine
→ final JSON
```

This is the layer Phase 13 should call.

# 📂 Important Files / Scripts

## ml/src/inference/inference_config.py

Stores Phase 12 paths, expected tensor contract, output locations, and version constants.

## ml/src/inference/result_schema.py

Defines dataclasses for prediction, segmentation, and full analysis output.

## ml/src/inference/analysis_pipeline.py

Main orchestration logic. It loads artifacts, validates a sequence, runs prediction, segmentation, scoring, and feedback.

## ml/src/inference/run_inference.py

CLI runner for offline inference. It can analyze a dataset sample by sample index or file name, or a standalone `[60,32]` sequence `.npy`.

## ml/src/inference/validate_inference_pipeline.py

Generates and validates Phase 12 sample output artifacts.

## ml/src/inference/tests/test_analysis_pipeline.py

Tests complete output generation, bad input shape handling, and invalid dataset lookup handling.

## ml/artifacts/phase12/sample_output.json

Stable example output for Phase 12.

## ml/artifacts/phase12/inference_health.json

Machine-readable validation status.

## ml/artifacts/phase12/inference_report.md

Human-readable validation report.

# 🔄 Data Flow

```text
X_sequence.npy sample
→ train-only scaler
→ Phase 8 best checkpoint
→ class probabilities
→ predicted shot
```

```text
same raw temporal sequence
→ Phase 9 segmenter
→ segment boundary and trigger metadata
```

```text
predicted shot + sequence
→ Phase 10 scoring templates
→ technique score and deviations
```

```text
score result
→ Phase 11 feedback engine
→ coaching tips and spoken feedback
```

```text
all results
→ Phase 12 JSON schema
```

# ⚠️ Common Mistakes / Pitfalls

- duplicating model prediction logic inside the API layer
- mixing raw video upload handling with ML business logic too early
- omitting debug metadata
- returning unstable JSON keys
- using scaled features for scoring or segmentation
- using raw unscaled features for model inference

# 💡 Key Engineering Decisions

## Use the Real Phase 8 Checkpoint

Phase 12 loads the selected Phase 8 checkpoint and scaler. This verifies that the trained model is actually part of inference.

## Preserve Raw Features for Scoring and Segmentation

The model uses scaled features. Segmentation and technique scoring use the original temporal feature values.

## Keep API Out of Phase 12

Phase 12 is offline. Phase 13 will add API transport on top of this module.

## Return More Than the Minimum JSON

The output includes the roadmap-required top-level fields plus nested prediction, segmentation, and source metadata for debugging.

# 📘 What I Should Write in Notes

- Phase 12 is orchestration, not new model training.
- The pipeline uses the real trained model and scaler.
- API code should call this pipeline instead of duplicating ML logic.
- Scaled features are only for the classifier.
- Raw features remain necessary for segmentation and scoring.
- Stable JSON output is the contract for Phase 13.

# 🧠 Personal Learning Insights

The key lesson is that ML systems become useful when modules are connected through stable contracts. A trained model alone is not an application. The inference layer turns model artifacts, scoring rules, and feedback rules into one usable analysis result.

Another lesson is separation of concerns. Building offline inference before API makes the system easier to test and safer to deploy.

# 🚀 Future Impact

Phase 12 prepares:

- Phase 13 API integration
- frontend response handling
- future raw-video inference orchestration
- production debugging
- eventual voice output through Phase 14

The next phase should expose this pipeline through an API without duplicating its logic.
