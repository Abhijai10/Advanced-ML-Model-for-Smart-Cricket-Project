# Smart Cricket Advanced ML Model

Smart Cricket Advanced ML Model is an AI cricket coaching project focused on analyzing full batting video sequences rather than single images.

## Goal

Build a system that can:
- capture full batting motion
- extract pose landmarks
- classify exactly one final cricket shot per motion
- prevent repeated predictions during a single swing
- generate technique match percentage
- compare user movement with ideal/pro-player references
- detect mistakes
- generate coaching feedback
- support future voice feedback
- support future website integration

## Current Phase

Phase 2 -> Pose Pipeline Development

Current label scope:
- shot_label
- quality_label

Detailed mistake labels are placeholders for future expansion.

## Current Progress

Completed:
- Phase 1 architecture setup
- Phase 2.1 label schema
- Phase 2.2 pose extraction
- Phase 2.3 robustness improvements
- Phase 2.4 preprocessing pipeline

## Initial Shot Classes

- cover_drive
- straight_drive
- pull_shot
- defensive_shot

## Folder Structure

```text
backend/
  app/
    routes/
    services/
    schemas/
  requirements.txt
ml/
  data/
    raw/
    processed/
    samples/
  notebooks/
  src/
    pose/
    preprocessing/
    features/
    training/
    feedback/
    utils/
  models/
  requirements.txt
docs/
  notes.md
  dataset_format.md
  architecture.md
README.md
.gitignore
```

## High-Level Pipeline

1. Input full batting video sequence.
2. Extract and preprocess body pose landmarks frame by frame.
3. Build motion sequence features over time.
4. Predict one final shot class for the completed motion.
5. Compute technique match percentage against ideal/pro-player references.
6. Identify mistakes and generate actionable coaching feedback.

## Pose Extraction Setup

This project uses the MediaPipe Pose Landmarker API for pose extraction.

- Manually download `pose_landmarker_full.task`.
- Place it at `ml/models/pose_landmarker_full.task`.
- This file is intentionally excluded from GitHub because it is a large pretrained dependency.

Current extraction flow:

`video` -> `OpenCV frame extraction` -> `MediaPipe pose detection` -> `JSON landmark generation` -> `pose normalization` -> `missing frame interpolation` -> `fixed-length sequence generation` -> `NumPy sequence output`
