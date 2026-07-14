# 📌 Current Project State

Current Phase:
- Phase 6 Completed (Temporal Dataset Infrastructure)
- Phase 7 Completed
- Phase 8 Completed — Temporal Model Training & Evaluation
- Preparing Phase 9 — Shot Segmentation

Project Architecture Status:
- Baseline tabular ML pipeline completed
- Temporal sequence-learning redesign completed
- Roadmap-aligned rank-3 dataset infrastructure completed
- GRU/BiLSTM-ready temporal dataset finalized
- temporal model architecture layer completed
- GRU architecture validated
- BiLSTM architecture validated

Project Status:
- Full preprocessing pipeline completed
- Full biomechanical feature engineering pipeline completed
- Temporal feature engineering redesign completed
- Rank-3 temporal tensor generation completed
- Temporal dataset infrastructure completed
- Temporal train/validation/test splitting completed
- Temporal dataset validation completed
- Temporal dataset packaging and manifest system completed
- Baseline tabular dataset preserved for comparison
- temporal dataset/model contract verification completed
- GRU temporal architecture completed
- BiLSTM temporal architecture completed
- temporal architecture validation completed
- model configuration system completed
- shape validation system completed
- pre-Phase-8 hardening completed
- bidirectional recurrent readout corrected to use final forward/backward hidden states
- player-overlap audit available for the current deterministic split
- Phase 8 experiment contract locked
- Phase 8 training pipeline completed
- train-only temporal feature scaler completed
- reproducibility and environment capture completed
- checkpointing and evaluation system completed
- bidirectional GRU and BiLSTM trained across seeds 42, 123, and 2026
- validation-selected best model artifact created

Current Outputs:

Baseline Tabular Dataset:
- ml/data/final/
- X_train.npy
- X_val.npy
- X_test.npy
- y_train.npy
- y_val.npy
- y_test.npy
- feature_schema.json
- label_mapping.json
- split_metadata.json
- dataset_manifest.json
- final_dataset_report.md

Primary Temporal Dataset:
- ml/data/final_temporal/
- X_sequence.npy
- y_sequence.npy
- X_train_sequence.npy
- X_val_sequence.npy
- X_test_sequence.npy
- y_train_sequence.npy
- y_val_sequence.npy
- y_test_sequence.npy
- temporal_feature_schema.json
- temporal_label_mapping.json
- temporal_split_metadata.json
- temporal_dataset_manifest.json
- temporal_dataset_report.md
- temporal_feature_validation_report.md
- temporal_feature_health.json

ml/src/models/
- __init__.py
- model_config.py
- gru_classifier.py
- test_gru_shapes.py
- bilstm_classifier.py
- test_bilstm_shapes.py
- model_utils.py
- validate_temporal_architectures.py

Pre-Phase-8 Hardening:
- ml/src/dataset_temporal/inspect_player_split_overlap.py
- Smart Cricket DOCS/00_CORE DOCS/Phase 8 Experiment Contract.md

Phase 8 Training Artifacts:
- ml/src/training/
- ml/artifacts/phase8/Phase 8 Training and Evaluation Report.md
- ml/artifacts/phase8/comparisons/model_comparison.json
- ml/artifacts/phase8/comparisons/final_test_metrics.json
- ml/artifacts/phase8/phase8_failure_analysis.md
- ml/artifacts/phase8/best_model/checkpoint.pt

Current Dataset Status:
- 80 validated ML samples
- 4 balanced cricket shot classes
- 60-frame fixed-length temporal sequences
- 32 engineered biomechanical features per frame
- Rank-3 temporal tensor dataset finalized

Primary Temporal Dataset:
```text 
X_sequence.shape = (80, 60, 32) 
```

Train / Validation / Test:
```
Train:      (56, 60, 32)
Validation: (12, 60, 32) 
Test:       (12, 60, 32) 
```

Baseline Dataset Preserved:
```text 
ml/data/final/ 
→ rank-2 tabular baseline 
```

---

# ✅ Completed Phases

## Phase 1 — Project Architecture & Setup
Completed:
- overall project structure
- preprocessing architecture
- modular pipeline planning
- repository setup

---

## Phase 2 — Pose Pipeline Setup
Completed:
- MediaPipe integration
- single-video pose extraction
- pose JSON generation pipeline

---

## Phase 2.5 — Dataset Building & Annotation
Completed:
- cricket shot dataset collection
- metadata.csv generation
- dataset organization
- quality labels
- use_for_v1 filtering

Dataset classes:
- cover_drive
- pull_shot
- defensive_shot
- sweep_shot

---

## Phase 3 — Batch Pose Extraction
Completed:
- batch extraction pipeline
- metadata-driven processing
- automatic pose JSON generation
- failure handling
- dry-run verification

Output:
- pose JSON files for all valid samples

---

## Phase 4 — Pose Cleaning & Normalization
Completed:
- pose inspection
- frame cleaning
- pose validation
- hip-centered normalization
- torso scaling
- body orientation alignment
- fixed-length sequence preparation

Final Output:
- 80 clean pose sequences
- 60 frames each
- MediaPipe landmarks:
  x, y, z, visibility

---

## Phase 5 — Feature Engineering
Completed:
- finalized 32-feature biomechanical design
- centralized feature blueprint system
- reusable geometry helper system
- joint-angle feature extraction
- posture feature extraction
- motion feature extraction
- shot-specific feature extraction
- full feature builder pipeline
- tabular feature dataset generation
- feature validation pipeline

Final Outputs:
- features.csv
- feature_validation_summary.json
- feature_statistics.csv

Feature Categories:
- Joint Angle Features
- Posture Features
- Motion Features
- Shot-specific Features

Validation Results:
- 80 successfully processed samples
- 0 NaN values
- 0 infinite values
- balanced 4-class dataset
- ML-ready feature representation prepared

---

## Phase 6 — ML Dataset Infrastructure & Temporal Redesign
Completed:
- feature schema system
- label encoding pipeline
- feature matrix generation
- deterministic dataset splitting
- dataset validation pipeline
- dataset packaging system
- dataset manifest generation
- reproducible ML dataset infrastructure

Final Outputs:
- X.npy
- y.npy
- X_train.npy
- X_val.npy
- X_test.npy
- y_train.npy
- y_val.npy
- y_test.npy
- feature_schema.json
- label_mapping.json
- split_metadata.json
- final_dataset_report.md
- dataset_manifest.json

Split Configuration:
- manual deterministic per-class stratified split
- train = 56
- validation = 12
- test = 12

Validation Results:
- all dataset artifacts validated successfully
- no NaN values
- no infinite values
- balanced class distributions across all splits
- feature schema consistency verified

---
## Phase 7 — Temporal Model Architecture Building

Completed:
- temporal dataset/model contract verification
- reusable temporal model configuration system
- GRU temporal architecture implementation
- BiLSTM temporal architecture implementation
- bidirectional hidden-state readout correction
- strengthened temporal input validation
- tensor shape validation pipeline
- architecture forward-pass validation
- parameter-count inspection system
- training-ready temporal model foundation

Official Tensor Contract:

```text
Input: [B, 60, 32]  
Output: [B, 4] 
```

Temporal Architectures:
- GRUClassifier
- BiLSTMClassifier

Validation Results:
- tensor contract verified
- GRU forward-pass validated
- BiLSTM forward-pass validated
- shape tests passing
- architecture compatibility confirmed
- current split audited as development/in-distribution; exact sample leakage absent
- player identity overlap may exist and must not be presented as unseen-player generalization
- Phase 8 experiment rules documented before training

Engineering Purpose:
- establish temporal motion-learning capability
- safely transition into Phase 8 training & evaluation
- preserve roadmap-aligned sequence learning

---
## Phase 8 — Temporal Model Training & Evaluation

Completed:
- PyTorch Dataset/DataLoader infrastructure for temporal tensors
- train-only feature standardization
- reproducibility controls and environment metadata
- supervised trainer for GRU/BiGRU and BiLSTM
- AdamW optimization with CrossEntropyLoss
- validation macro-F1 checkpoint selection
- early stopping, gradient clipping, and learning-rate scheduling
- per-seed metrics, histories, plots, predictions, and checkpoints
- model comparison and selected best-model artifact
- final holdout test evaluation
- failure analysis with sample traceability
- person-overlap limitation documented

Official Experiments:
```text
bigru:  seeds 42, 123, 2026
bilstm: seeds 42, 123, 2026
```

Aggregate Validation Results:
```text
bigru:  mean macro F1 = 0.8353, std = 0.0031, mean accuracy = 0.8333
bilstm: mean macro F1 = 0.7236, std = 0.0471, mean accuracy = 0.7222
```

Selected Model:
```text
bidirectional GRU (bigru)
```

Selected Checkpoint:
```text
ml/artifacts/phase8/best_model/checkpoint.pt
```

Final Holdout Test Results:
```text
accuracy        = 0.6667
macro precision = 0.7083
macro recall    = 0.6667
macro F1        = 0.6762
weighted F1     = 0.6762
```

Confusion Matrix Summary:
- cover_drive predicted as sweep_shot: 1
- defensive_shot predicted as sweep_shot: 1
- pull_shot predicted as defensive_shot: 1
- sweep_shot predicted as pull_shot: 1

Generalization Limitation:
- current metrics represent sample-stratified, in-distribution development performance
- current split is not person-disjoint
- results must not be presented as unseen-player generalization

---
# 📂 Current Dataset State

Total Videos:
- 84

Training Samples:
- 80

Sequence Length:
- 60 frames

Landmarks:
- 33 MediaPipe pose landmarks

Current ML Dataset:
- 32 engineered biomechanical features
- encoded shot labels
- deterministic dataset splits
- ML-ready NumPy arrays
- dataset manifests and validation reports

Current Final Splits:
- Train: 56
- Validation: 12
- Test: 12

---

# 🔒 Locked Engineering Decisions

## Pose Pipeline
Locked:
- MediaPipe Pose extraction
- JSON-based pose storage

---

## Preprocessing Pipeline
Locked:
- frame cleaning
- visibility filtering
- hip-centered normalization
- torso-length scaling
- shoulder-based alignment
- fixed-length sequences

---

## Sequence Design
Locked:
- 60-frame sequences
- uniform downsampling
- frame duplication for short clips

---

## Feature Engineering Design
Locked:
- curated biomechanical feature engineering
- explainable feature design
- modular feature extraction architecture
- centralized feature blueprint system
- 32-feature representation
- fixed feature ordering for ML consistency

Feature Categories:
- Joint Angle Features
- Posture Features
- Motion Features
- Shot-specific Features

---

## Dataset Infrastructure Design
Locked:
- schema-driven dataset pipeline
- deterministic per-class stratified splitting
- reproducible dataset packaging
- artifact validation system
- dataset manifest architecture
- fixed label encoding system
- current 56/12/12 temporal split is a development/in-distribution split, not a person-disjoint generalization proof

---

# 🧠 Current ML Direction

Current ML Stage:
- Temporal model training complete; preparing shot segmentation

Temporal architectures completed:
- GRU
- BiLSTM

Primary Trained Models:
- bidirectional GRU
- BiLSTM

Purpose:
- temporal cricket shot classification
- motion progression understanding
- sequence-aware biomechanical learning

Future Baseline Comparison Models:
- Logistic Regression
- Random Forest
- Support Vector Machine (SVM)

Purpose:
- baseline benchmarking
- temporal vs tabular comparison
- feature sanity checking

Long-Term Direction:
- temporal motion intelligence
- technique scoring
- coaching feedback generation
- real-time inference
- webcam-based batting analysis

Important Constraint:
- avoid overengineering early versions
- prioritize generalization
- prevent overfitting on small datasets
- stabilize temporal training before advanced architectures

---

# 🏗️ Current Pipeline Flow

Raw Video
→ Pose Extraction
→ Pose JSON
→ Cleaning
→ Normalization
→ Alignment
→ Fixed-Length Sequences
→ Per-Frame Temporal Feature Extraction
→ Temporal Feature Validation
→ Rank-3 Tensor Construction

```text
[samples, time_steps, feature_dim] 
```

→ Temporal Dataset Validation
→ Temporal Dataset Packaging
→ Temporal Model Architecture Building
→ Temporal Architecture Validation
→ GRU / BiLSTM Training
→ Phase 8 Best Temporal Checkpoint
→ Shot Segmentation
→ Future Technique Understanding
→ Future Coaching Feedback Engine

---

# ⚠️ Current Constraints

- relatively small dataset (~80 samples)
- need strong generalization
- avoid overfitting
- maintain explainable ML pipeline
- preserve reproducibility
- maintain modular architecture

Current Technical Observations:
- dataset validation passed successfully
- deterministic split system operational
- all dataset artifacts validated
- reproducible dataset infrastructure completed
- GRU architecture validated successfully
- BiLSTM architecture validated successfully
- tensor contract verification passed
- shape validation system operational
- Phase 8 training and evaluation completed
- selected bidirectional GRU reached final holdout test macro F1 of 0.6762
- validation/test gap and 56-sample training size indicate overfitting risk remains

Observed Engineering Concerns:
- limited dataset size for deep sequence models
- some motion-related features may require redesign in future iterations
- future scaling will require larger and more diverse cricket datasets
- current split is not person-disjoint, so unseen-player claims are not supported

Current Engineering Decision:
- prioritize roadmap-aligned temporal sequence learning
- carry the validation-selected bidirectional GRU checkpoint into later temporal phases
- prevent overfitting through careful regularization
- stabilize temporal training before architectural expansion

---

# 🔄 Things Likely To Evolve Later

Possible Future Changes:
- dataset expansion
- more shot classes
- advanced segmentation
- sequence-model experimentation
- inference optimization
- coaching feedback refinement

Likely Stable Components:
- preprocessing pipeline
- pose normalization strategy
- sequence structure
- feature categories
- dataset infrastructure philosophy

---

# 🚀 Current Focus

Current Work:
- Preparing Phase 9 — Shot Segmentation

Immediate Goals:
- design shot segmentation boundaries
- preserve Phase 8 checkpoint/evaluation traceability
- avoid changing the locked Phase 8 dataset split or model-selection record
- plan how segmented clips will feed the existing temporal model contract

Next Major Milestone:
Roadmap-aligned shot segmentation layer that can feed the trained temporal classifier.

---

# 📘 Important Engineering Philosophy

This project prioritizes:
- modularity
- explainability
- production-style architecture
- reproducibility
- sequence understanding
- biomechanical reasoning
- iterative engineering

The goal is NOT only shot classification.

The goal is:
- technique understanding
- mistake detection
- intelligent feedback generation
- future real-time AI cricket coaching system
