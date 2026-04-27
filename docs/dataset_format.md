# Dataset Format

This document defines the required dataset structure for the Smart Cricket Advanced ML Model.

## Required Dataset Structure

```text
ml/data/
  raw/
    user_videos/
      cover_drive/
      straight_drive/
      pull_shot/
      defensive_shot/
    ideal_references/
      cover_drive/
      straight_drive/
      pull_shot/
      defensive_shot/
  processed/
    pose_json/
      cover_drive/
      straight_drive/
      pull_shot/
      defensive_shot/
    metadata/
      sequence_metadata.csv
  samples/
    sample_labels.csv
```

## 1. Raw Videos

Path: `ml/data/raw/user_videos/`  
Contains original batting videos uploaded or collected for training/inference preparation.

- Keep one video per batting attempt.
- Organize by shot folder for easier curation.
- Example file: `ml/data/raw/user_videos/cover_drive/user_001.mp4`

## 2. Processed Pose JSON

Path: `ml/data/processed/pose_json/`  
Contains extracted pose landmarks per video sequence.

- One JSON file per source video.
- Store frame-wise landmarks (x, y, optional z, visibility) and timestamps/frame indices.
- Example file: `ml/data/processed/pose_json/cover_drive/user_001.json`

## 3. Metadata CSV

Path: `ml/data/processed/metadata/sequence_metadata.csv`  
Central table describing each sequence and its labels.

Minimum recommended columns:
- `sequence_id` (unique id)
- `video_path` (raw video location)
- `pose_json_path` (processed pose file location)
- `shot_label` (required)
- `quality_label` (required)
- `split` (train/val/test)
- `fps`
- `num_frames`

## 4. Ideal Reference Clips

Path: `ml/data/raw/ideal_references/`  
Contains high-quality reference clips (coach/pro-style) used for technique comparison.

- Organize by shot class.
- Example file: `ml/data/raw/ideal_references/straight_drive/ref_pro_01.mp4`

## 5. Sample Labels

Path: `ml/data/samples/sample_labels.csv`  
Small example label file for quick testing and pipeline validation before full dataset preparation.

Minimum columns:
- `video_name`
- `shot_label`
- `quality_label`

## Label Definitions

- `shot_label`: final shot class for one complete batting motion.  
  Current values: `cover_drive`, `straight_drive`, `pull_shot`, `defensive_shot`.
- `quality_label`: overall technique quality class.  
  Current values: `good`, `average`, `bad`.
- `future_mistake_labels`: planned future labels for detailed error analysis (for example: early_swing, closed_shoulder, poor_footwork, weak_follow_through).

## Sample Folder Examples

```text
ml/data/raw/user_videos/cover_drive/user_001.mp4
ml/data/raw/user_videos/pull_shot/user_014.mp4
ml/data/raw/ideal_references/defensive_shot/ref_coach_02.mp4
ml/data/processed/pose_json/cover_drive/user_001.json
ml/data/processed/metadata/sequence_metadata.csv
ml/data/samples/sample_labels.csv
```
## Current Dataset Requirement (Phase 2 Checkpoint)

Before model training begins:

- 40–50 user videos
- 10–15 pro reference clips

User video ratio per shot:
- 4–5 good
- 4–6 average
- 2–3 bad

Current shot classes:
- cover_drive
- straight_drive
- pull_shot
- defensive_shot