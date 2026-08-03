# 🏏 Smart Cricket — Advanced ML Model

## 🚀 Project Overview

Smart Cricket is an AI-powered cricket analytics system designed to analyze batting shots using pose estimation and motion analysis.

Instead of relying on single images, this project processes full video sequences, extracts human pose keypoints, and converts them into structured data for:

- Shot classification  
- Motion understanding  
- Future real-time feedback system  

---

## 🛠️ Technologies Used

### Computer Vision & Pose Estimation
- MediaPipe Pose
- OpenCV

### Machine Learning & Data Processing
- NumPy
- Pandas
- scikit-learn

### Visualization & Analysis
- Matplotlib

### Development Environment
- Python
- macOS (Apple Silicon)
- AI-assisted engineering workflow (Cursor + Codex)

---

## 📊 Current Progress

The project is being developed through structured ML engineering phases:

- ✅ Phase 1: Project Architecture & Setup  
- ✅ Phase 2: Pose Pipeline Setup  
- ✅ Phase 2.5: Dataset Building & Annotation  
- ✅ Phase 3: Batch Pose Extraction  
- ✅ Phase 4: Pose Cleaning & Normalization  
- ✅ Phase 5: Feature Engineering (Tabular Baseline)  
- ✅ Phase 5.5: Temporal Feature Engineering Redesign  
- ✅ Phase 6: Temporal ML Dataset Infrastructure  
- ✅ Phase 7: Temporal Model Architecture Building 
- ✅ Pre-Phase-8 Hardening: Architecture & Experiment Readiness Gate
- ✅ Phase 8: Temporal Model Training & Evaluation
- ✅ Phase 9: Shot Segmentation
- ✅ Phase 10: Technique Scoring System
- ✅ Phase 11: Feedback Engine
- ✅ Phase 12: Offline Inference Pipeline
- ✅ Phase 13: API Integration
- ✅ Phase 14: Voice Output

Current development is now focused on:

```text
Production hardening, deployment readiness, and honest field validation
```


---

### ✅ Current System Capabilities

The Smart Cricket pipeline now converts raw cricket batting videos into a fully validated, reproducible, and temporal ML-ready dataset.

Current completed outputs:

- Cleaned and normalized pose sequences  
- Orientation-aligned batting motion data  
- Fixed-length temporal sequences (60 frames)  
- Per-frame biomechanical feature extraction  
- 32 engineered temporal motion features  
- Rank-3 temporal tensors for sequence learning  
- Stable label encoding pipeline  
- Deterministic train/validation/test splits  
- Full dataset validation system  
- Dataset manifests and metadata registry  
- Complete GRU/BiLSTM-ready dataset infrastructure  
- Verified temporal model architectures (GRU / BiLSTM) 
- Correct bidirectional recurrent hidden-state readout
- Strong temporal model input validation
- Player-overlap audit for the current development split
- Locked Phase 8 experiment contract
- Completed Phase 8 temporal training and evaluation
- Validation-selected bidirectional GRU checkpoint for later phases
- Explainable Phase 9 shot segmentation state machine
- Single-prediction trigger validation for all 80 finalized sequences
- Rule-based Phase 10 technique scoring from measurable biomechanical deviations
- Shot-specific ideal technique templates derived from train-split references
- Component-level scoring prepared for the Phase 11 feedback engine
- Rule-based Phase 11 coaching feedback generated from feature-linked technique issues
- TTS-friendly spoken feedback strings prepared for future voice output
- Offline Phase 12 inference pipeline returning stable structured JSON
- Integrated prediction, segmentation, scoring, and feedback orchestration for finalized temporal sequences
- Phase 13 FastAPI backend wrapper with `/health` and `/analyze`
- Frontend-consumable API response that calls the Phase 12 pipeline without duplicating ML logic
- Phase 14 voice output layer that converts `spoken_feedback` into playable audio metadata/artifacts
- Frontend audio-ready response with text + audio file metadata
- React website/app shell with camera capture, Supabase auth integration, analysis history, and shot charts
- Production `/analyze` path now uses uploaded bytes only, not trusted filenames
- Dev-only stored dataset analysis endpoint is isolated behind an environment flag
- API readiness checks, request IDs, configurable CORS, upload validation, rate limiting, and optional Supabase JWT verification
- Browser-accessible per-request audio artifacts and frontend audio playback

Current temporal dataset contract:

```text
X_sequence.shape = (80, 60, 32)

80 batting shots
→ 60 frames per shot
→ 32 biomechanical features per frame
```  

---

### 📦 Temporal Dataset Status

### Full Temporal Dataset

```text
X_sequence.shape = (80, 60, 32)
y_sequence.shape = (80,)
```

### Train / Validation / Test Splits

```text
Train:
X_train_sequence.shape = (56, 60, 32)

Validation:
X_val_sequence.shape = (12, 60, 32)

Test:
X_test_sequence.shape = (12, 60, 32)
```

### Dataset Summary

- Total ML samples: 80  
- Sequence length: 60 frames  
- Temporal feature dimension: 32  
- Classes: 4 balanced cricket shot categories  
- Train split: 56 samples  
- Validation split: 12 samples  
- Test split: 12 samples  

The project now contains a fully validated and packaged temporal machine-learning dataset ready for:

- GRU training  
- BiLSTM training  
- temporal motion learning  
- sequence-aware cricket shot classification  

Phase 8 trained the official bidirectional GRU and BiLSTM architectures across seeds 42, 123, and 2026. Model selection used validation macro F1 only, then evaluated the selected checkpoint once on the holdout test split.

Phase 8 result summary:

- Selected model: bidirectional GRU (`bigru`)
- Mean validation macro F1: `0.8353`
- Mean validation accuracy: `0.8333`
- Final holdout test accuracy: `0.6667`
- Final holdout test macro F1: `0.6762`
- Best checkpoint: `ml/artifacts/phase8/best_model/checkpoint.pt`

Important limitation:

- The official split is deterministic and class-balanced, but not person-disjoint. These results represent sample-stratified, in-distribution development performance, not proof of unseen-player generalization.

Phase 9 then added the shot segmentation and prediction-gating layer:

- Segmentation strategy: explainable motion-energy thresholds + state machine
- State path: `idle → preparation → backswing → swing → follow_through → completed → cooldown`
- Validation result: `80/80` finalized clips produced one detected segment
- Single-trigger result: `80/80` finalized clips produced exactly one prediction trigger
- Debug report: `ml/artifacts/phase9/segmentation_debug_report.md`

Phase 10 adds the first interpretable technique scoring layer:

- Scoring strategy: rule-based template matching
- Template source: train split, preferring good-quality examples when enough are available
- Score range: `0-100`
- Components: head stability, front-foot commitment, lead elbow, knee bend, weight transfer, follow-through, rotation, and balance
- Test samples scored: `12`
- Mean technique match score: `84.6328`
- Minimum technique match score: `53.6322`
- Maximum technique match score: `97.0846`
- Classifier confidence used as technique score: `False`
- Report: `ml/artifacts/phase10/technique_score_report.json`

Phase 11 turns technique scores and deviations into readable coaching feedback:

- Feedback strategy: editable rule-based coaching rules
- Input source: Phase 10 `technique_score_report.json`
- Samples processed: `12`
- Detected feature-linked issues: `26`
- Spoken feedback present: `12/12`
- Validation passed: `True`
- Sample outputs: `ml/artifacts/phase11/sample_feedback_outputs.json`

Phase 12 connects the core ML modules into one offline analysis result:

- Pipeline mode: finalized temporal sequence inference
- Input contract: `[60, 32]`
- Sample index validated: `1`
- Predicted shot: `cover_drive`
- Shot confidence: `0.9918`
- Technique match score: `96.4375`
- Segmentation completed: `True`
- Output schema stable: `True`
- Sample output: `ml/artifacts/phase12/sample_output.json`

Phase 13 exposes the analysis pipeline through a backend API:

- API framework: FastAPI
- Health endpoint: `GET /health`
- Analyze endpoint: `POST /analyze`
- Sample upload filename: `cover_drive_average_02.mov`
- Analyze status code: `200`
- Unknown video error status code: `422`
- Validation passed: `True`
- Sample response: `ml/artifacts/phase13/sample_api_response.json`

Phase 14 adds the voice output layer:

- Input: Phase 13 `spoken_feedback`
- Output audio format: `wav`
- Audio provider used in this environment: `local_audio_cue_wav`
- Audio generated: `True`
- Audio playable: `True`
- Audio bytes: `213580`
- Frontend audio-ready response: `ml/artifacts/phase14/frontend_audio_ready_response.json`
- Audio file: `ml/artifacts/phase14/audio_output/sample_spoken_feedback.wav`

Important split interpretation:

- The current deterministic 56/12/12 split is useful for development and in-distribution evaluation.
- It is not a person-disjoint split and must not be presented as proof of unseen-player generalization.

## Production Setup

Install and verify everything from a clean checkout:

```bash
scripts/setup.sh
scripts/test.sh
```

Copy `.env.example` to `.env` and configure the API/frontend variables before deployment.

Key references:

- `docs/PRODUCTION_READINESS.md`
- `docs/MODEL_CARD.md`
- `docs/DATASET_CARD.md`
- `docs/DEPLOYMENT.md`

## Honest Readiness Note

Smart Cricket is not yet a fully validated commercial coaching product. The product architecture is now much closer to production, but final readiness still depends on a real Supabase deployment, server-side persistence, player-held-out evaluation on a larger dataset, coach validation, and production TTS/provider credentials where needed.
- Future unseen-player evaluation should use a documented player-held-out protocol.

---

## 📁 Dataset Information

- Total videos: 84  
- Training videos (use_for_v1 = yes): 80  

### Shot Classes:
- cover_drive  
- pull_shot  
- defensive_shot  
- sweep_shot  

Dataset selection is controlled using:

metadata.csv → use_for_v1 column

---

## ⚙️ Complete ML Pipeline

Raw Cricket Videos  
↓  
Pose Extraction (MediaPipe)  
↓  
Pose Landmark JSON Files  
↓  
Pose Cleaning & Validation  
↓  
Pose Normalization  
↓  
Body Orientation Alignment  
↓  
Fixed-Length Temporal Sequences (60 Frames)  
↓  
Per-Frame Biomechanical Feature Extraction  
↓  
Temporal Feature Validation  
↓  
Rank-3 Tensor Construction  

```text
[samples, time_steps, feature_dim]
```

↓  
Temporal Label Encoding  
↓  
Temporal Train / Validation / Test Splitting  
↓  
Temporal Dataset Validation  
↓  
Temporal Dataset Packaging & Manifest  
↓  
GRU / BiLSTM-Ready Dataset Infrastructure 
↓  
GRU / BiLSTM Temporal Model Architecture  
↓  
Temporal Architecture Validation  
↓  
Pre-Phase-8 Hardening & Experiment Contract  
↓  
Phase 8 Training & Evaluation
↓
Phase 9 Shot Segmentation & Prediction Gating
↓
Phase 10 Technique Scoring
↓
Phase 11 Feedback Engine
↓
Phase 12 Offline Inference Pipeline
↓
Phase 13 API Integration
↓
Phase 14 Voice Output

---

### 🧠 Final Temporal Dataset Artifacts

The finalized temporal dataset layer now includes:

### Core Temporal Tensors

- `X_sequence.npy`
- `y_sequence.npy`

### Train / Validation / Test Tensors

- `X_train_sequence.npy`
- `X_val_sequence.npy`
- `X_test_sequence.npy`

- `y_train_sequence.npy`
- `y_val_sequence.npy`
- `y_test_sequence.npy`

### Schema & Labeling

- `temporal_feature_schema.json`
- `temporal_label_mapping.json`
- `temporal_label_encoder.pkl`

### Dataset Metadata

- `temporal_split_metadata.json`
- `temporal_dataset_manifest.json`

### Validation & Health Reports

- `temporal_dataset_report.md`
- `temporal_feature_validation_report.md`
- `temporal_feature_statistics.csv`
- `temporal_feature_health.json`

### Traceability

- `temporal_dataset_index.csv`
- `train_temporal_index.csv`
- `val_temporal_index.csv`
- `test_temporal_index.csv`

This creates a fully reproducible and training-ready temporal ML dataset system for:

- GRU training  
- BiLSTM training  
- temporal motion intelligence

---

## 🚀 Phase 4 — Pose Cleaning & Normalization (Completed)

In this phase, raw pose data was transformed into a clean, structured, and ML-ready format.

### 🔹 Key Objectives

- Remove noisy or invalid frames  
- Normalize pose coordinates for consistency  
- Align body orientation across samples  
- Convert variable-length sequences into fixed-length inputs  

---

### 🔹 Steps Implemented

#### 1. Pose Data Inspection
- Analyzed dataset quality  
- Checked frame counts, missing landmarks, and visibility  

#### 2. Data Cleaning
- Removed frames with:
  - missing landmarks  
  - low visibility  

#### 3. Data Validation
- Verified:
  - JSON structure  
  - numeric landmark values  
  - consistent frame sequences  

#### 4. Coordinate Normalization
- Centered poses using hip midpoint  
- Scaled using torso length  

#### 5. Body Orientation Alignment
- Rotated poses to standard orientation  
- Reduced rotational variance  

#### 6. Fixed-Length Sequence Preparation
- Converted all sequences to 60 frames  
- Used uniform sampling and frame duplication  

---

### 📊 Final Dataset

- Total samples: 80 sequences  
- Sequence length: 60 frames each  
- Format: MediaPipe landmarks (x, y, z, visibility)  

---

## 🧠 Phase 5 — Feature Engineering (Completed)

In this phase, processed pose sequences were converted into structured biomechanical feature representations for machine learning.

The system extracts cricket-specific motion and posture information from each batting sequence and converts it into structured temporal biomechanical representations.

Instead of compressing an entire batting shot into one summarized vector, the final system preserves frame-by-frame motion evolution for temporal learning.

---

## 🔹 Feature Categories

The final feature system contains 32 engineered biomechanical features grouped into four categories:

### 1. Joint Angle Features
Captures body shape and joint mechanics.

Examples:
- elbow angles  
- knee angles  
- hip rotation  
- shoulder rotation  

---

### 2. Posture Features
Captures body balance and alignment.

Examples:
- trunk lean  
- head stability  
- stance width  
- shoulder-hip separation  

---

### 3. Motion Features
Captures temporal movement and speed.

Examples:
- wrist velocities  
- body motion  
- rotational movement  
- motion energy  

---

### 4. Shot-Specific Features
Captures cricket-specific technique patterns.

Examples:
- front-foot commitment  
- follow-through extension  
- weight transfer  
- elbow extension changes  

---

## 🔹 Feature Dataset Evolution

### Baseline Tabular Dataset

Initial feature engineering produced:

```text
(80, 32)
```

This representation was useful for:

- classical ML baselines  
- feature experimentation  
- engineering comparison  

---

### Final Temporal Dataset

The final redesigned system produces:

```text
(80, 60, 32)
```

Meaning:

```text
80 batting shots
→ 60 frames per shot
→ 32 engineered features per frame
```

This preserves temporal motion information required for:

- GRU sequence learning  
- BiLSTM temporal modeling  
- motion progression understanding

---

## 🧠 Phase 6 — ML Dataset Infrastructure (Baseline + Temporal Upgrade)

In this phase, engineered biomechanical features were transformed into a fully reproducible machine-learning dataset infrastructure.

This phase created the bridge between:

Pose & Feature Engineering  
→  
Machine Learning Training Pipeline

---

### 🔹 Major Objectives

- Create stable ML-ready feature matrices  
- Encode cricket shot labels consistently  
- Build deterministic train/validation/test splits  
- Validate all dataset artifacts  
- Package the dataset into a reusable ML infrastructure layer  

---

### 🔹 Key Systems Implemented

#### 1. Feature Schema System
Created a stable schema describing:

- feature ordering  
- target labels  
- metadata structure  
- dataset contracts  

Artifact:
- `feature_schema.json`

---

#### 2. Label Encoding Pipeline

Created a reproducible label encoding system for cricket shot classes.

Examples:

- cover_drive → 0  
- defensive_shot → 1  
- pull_shot → 2  
- sweep_shot → 3  

Artifacts:
- `label_encoder.pkl`
- `label_mapping.json`

---

#### 3. Feature Matrix Construction

Converted engineered biomechanical features into ML-ready numerical arrays:

- `X.npy`
- `y.npy`

Final dataset shape:

- 80 samples  
- 32 engineered features  

---

#### 4. Deterministic Dataset Splitting

Implemented manual deterministic per-class stratified splitting.

Per class:

- 14 train  
- 3 validation  
- 3 test  

Final dataset splits:

- Train: 56 samples  
- Validation: 12 samples  
- Test: 12 samples  

---

#### 5. Dataset Validation System

Created validation pipelines to verify:

- feature consistency  
- split integrity  
- class distributions  
- artifact correctness  
- dataset reproducibility  

Artifact:
- `final_dataset_report.md`

---

#### 6. Dataset Packaging & Manifest System

Created a centralized dataset manifest registry describing all ML dataset artifacts and dependencies.

Artifact:
- `dataset_manifest.json`

---

### 📊 Final ML Dataset

The Smart Cricket project now contains a complete ML-ready dataset layer with:

- validated feature matrices  
- encoded targets  
- reproducible splits  
- traceable metadata  
- packaged dataset infrastructure  

This allows future model training pipelines to directly load finalized datasets without re-running preprocessing stages.

---

## 🧠 Phase 7 — Temporal Model Architecture Building (Completed)

In this phase, the finalized temporal cricket dataset was converted into trainable temporal deep-learning model architectures.

This phase created the bridge between:

Temporal Dataset Infrastructure  
→  
Temporal Model Learning

The goal was not training yet.

Instead, Phase 7 focused on:

- temporal architecture correctness  
- dataset/model compatibility  
- tensor validation  
- reproducible model configuration  

---

### 🔹 Temporal Dataset Contract

Official temporal tensor:

```text
X_sequence.shape = (80, 60, 32)
```
Meaning :
```
80 batting shots
→ 60 frames per shot
→ 32 biomechanical features per frame
```
Model input contract:
```
[B, 60, 32]
```
Model output contract:
```
[B, 4]
```
---
### 🔹 Temporal Architectures Implemented

#### 1. GRUClassifier

A lightweight temporal baseline model designed for sequence learning with lower overfitting risk.

Pipeline:
```
Temporal sequence
→ GRU encoder
→ final timestep representation
→ classification head
→ shot logits
```
Parameter count:
```
421,892
```
---
#### 2. BiLSTMClassifier

A bidirectional temporal model designed to understand full-shot motion context.

Pipeline:
```
Temporal sequence
→ Bidirectional LSTM
→ final timestep representation
→ classification head
→ shot logits
```
Parameter count:
```
562,180
```
### 🔹 Architecture Validation

Phase 7 included architecture validation before training.

Validation included:

* temporal tensor compatibility
* GRU forward-pass testing
* BiLSTM forward-pass testing
* shape validation
* bad-rank failure handling

Verified tensor flow:
```
Input:
[4, 60, 32]

Output:
[4, 4]
```
This ensured the models were fully compatible with the finalized temporal dataset before Phase 8 training.

---

## 🧪 Phase 8 — Temporal Model Training & Evaluation (Completed)

Phase 8 added the reproducible training and evaluation layer for the temporal dataset.

Implemented systems:

- PyTorch temporal Dataset/DataLoader infrastructure
- Train-only feature standardization
- Reproducibility and environment capture
- Supervised GRU/BiLSTM trainer
- Validation macro-F1 checkpointing
- Early stopping, gradient clipping, and AdamW optimization
- Per-seed metrics, histories, checkpoints, plots, and predictions
- Model comparison and best-model selection
- Final holdout test evaluation
- Failure analysis and person-overlap limitation reporting

Models trained:

```text
bigru seeds: 42, 123, 2026
bilstm seeds: 42, 123, 2026
```

Aggregate validation comparison:

```text
bigru  mean macro F1 = 0.8353, std = 0.0031, params = 421,892
bilstm mean macro F1 = 0.7236, std = 0.0471, params = 562,180
```

Final selected checkpoint:

```text
ml/artifacts/phase8/best_model/checkpoint.pt
```

Final holdout test metrics for selected `bigru` checkpoint:

```text
accuracy        = 0.6667
macro precision = 0.7083
macro recall    = 0.6667
macro F1        = 0.6762
weighted F1     = 0.6762
```

Primary Phase 8 artifacts:

- `ml/artifacts/phase8/Phase 8 Training and Evaluation Report.md`
- `ml/artifacts/phase8/comparisons/model_comparison.json`
- `ml/artifacts/phase8/comparisons/final_test_metrics.json`
- `ml/artifacts/phase8/phase8_failure_analysis.md`
- `ml/artifacts/phase8/best_model/`

---

## 🎬 Phase 9 — Shot Segmentation (Completed)

Phase 9 prevents unstable repeated predictions during one batting motion.

Instead of treating every frame as a prediction opportunity, the system now creates one final prediction trigger per detected shot segment.

Core idea:

```text
motion stream → segmentation state machine → one completed shot → one prediction trigger
```

Implemented systems:

- motion-energy extraction from the official 32-D temporal feature schema
- smoothing and robust per-sequence normalization
- explainable state machine:

```text
idle
→ preparation
→ backswing
→ swing
→ follow_through
→ completed
→ cooldown
```

- cooldown logic to suppress repeated triggers
- segment summary CSV
- per-frame state trace CSV
- segmentation health JSON
- debug report
- unit tests for motion energy, state transitions, cooldown, and single-shot triggering

Validation on the finalized temporal dataset:

```text
Input: X_sequence.npy = (80, 60, 32)
Segments detected: 80 / 80
Single-trigger sequences: 80 / 80
Sequence-end completions: 65
Validation passed: True
```

Important interpretation:

- The current dataset already contains clipped one-shot sequences, so many clips complete at sequence end.
- This is acceptable for finalized clips and is explicitly reported.
- Live-stream segmentation will need separate buffering and latency validation in later phases.
- Phase 9 itself does not retrain the Phase 8 classifier; Phase 10 now consumes its stabilized prediction boundary.

Primary Phase 9 artifacts:

- `ml/artifacts/phase9/segmentation_debug_report.md`
- `ml/artifacts/phase9/segmentation_health.json`
- `ml/artifacts/phase9/segmentation_segments.csv`
- `ml/artifacts/phase9/segmentation_state_trace.csv`

---

## 🧮 Phase 10 — Technique Scoring System (Completed)

Phase 10 separates shot recognition from shot quality.

The classifier answers:

```text
What shot does the model think this is?
```

The technique scoring system answers:

```text
How well does the movement match measurable reference mechanics for that shot?
```

Core idea:

```text
predicted shot + temporal features + ideal templates
→ component scores
→ technique_match_score
```

Implemented systems:

- `ml/src/scoring/score_config.py`
- `ml/src/scoring/technique_scoring.py`
- `ml/src/scoring/validate_technique_scoring.py`
- `ml/src/scoring/tests/test_technique_scoring.py`

Scoring components:

- `head_stability_score`
- `front_foot_commitment_score`
- `lead_elbow_score`
- `knee_bend_score`
- `weight_transfer_score`
- `follow_through_score`
- `rotation_score`
- `balance_score`

Primary Phase 10 artifacts:

- `ml/artifacts/phase10/ideal_template_schema.json`
- `ml/artifacts/phase10/technique_scores.csv`
- `ml/artifacts/phase10/technique_score_report.json`
- `ml/artifacts/phase10/technique_score_report.md`
- `ml/artifacts/phase10/technique_scoring_health.json`

Validation result:

```text
Templates created: 4
Components per template: 8
Samples scored: 12
Score range valid: True
Validation passed: True
```

Important interpretation:

- Technique scores are v1 template-match scores, not coach-certified biomechanical truth labels.
- Phase 10 does not use classifier confidence as technique quality.
- The templates are train-split-derived because professional reference clips are not yet available.
- Phase 11 now consumes component scores and deviation summaries to generate specific coaching feedback.

---

## 🗣️ Phase 11 — Feedback Engine (Completed)

Phase 11 makes Smart Cricket feel more like a coach instead of only a classifier.

Core idea:

```text
component scores + feature deviations
→ detected issues
→ coaching tips
→ detailed feedback
→ spoken feedback
```

Implemented systems:

- `ml/src/feedback/feedback_schema.py`
- `ml/src/feedback/feedback_rules.py`
- `ml/src/feedback/feedback_templates.py`
- `ml/src/feedback/feedback_engine.py`
- `ml/src/feedback/validate_feedback_engine.py`
- `ml/src/feedback/tests/test_feedback_engine.py`

Primary Phase 11 artifacts:

- `ml/artifacts/phase11/sample_feedback_outputs.json`
- `ml/artifacts/phase11/feedback_outputs.csv`
- `ml/artifacts/phase11/feedback_report.md`
- `ml/artifacts/phase11/feedback_health.json`

Validation result:

```text
Samples processed: 12
Detected issues: 26
Spoken feedback present: True
Issues linked to features: True
Validation passed: True
```

Important interpretation:

- Feedback is generated from measurable Phase 10 deviations.
- The system explains what to improve, why it matters, and how to improve it.
- Spoken feedback is concise and suitable for future TTS, but Phase 11 does not implement voice output.
- The feedback is coaching-style guidance, not a certified biomechanical diagnosis.

---

## 🔄 Phase 12 — Offline Inference Pipeline (Completed)

Phase 12 connects the completed ML subsystems into one stable offline analysis pipeline.

Core idea:

```text
temporal sequence
→ model prediction
→ segmentation/gating
→ technique scoring
→ feedback generation
→ final JSON
```

Implemented systems:

- `ml/src/inference/inference_config.py`
- `ml/src/inference/result_schema.py`
- `ml/src/inference/analysis_pipeline.py`
- `ml/src/inference/run_inference.py`
- `ml/src/inference/validate_inference_pipeline.py`
- `ml/src/inference/tests/test_analysis_pipeline.py`

Primary Phase 12 artifacts:

- `ml/artifacts/phase12/sample_output.json`
- `ml/artifacts/phase12/inference_health.json`
- `ml/artifacts/phase12/inference_report.md`

Validation result:

```text
Sample index: 1
Predicted shot: cover_drive
Shot confidence: 0.9918
Technique match score: 96.4375
Segmentation completed: True
Validation passed: True
```

Important interpretation:

- Phase 12 v1 is an offline pipeline over finalized temporal feature sequences.
- It uses the real Phase 8 checkpoint, Phase 9 segmenter, Phase 10 scorer, and Phase 11 feedback engine.
- Raw video upload handling belongs to Phase 13 API integration.
- Voice/TTS output remains Phase 14.

---

## 🌐 Phase 13 — API Integration (Completed)

Phase 13 exposes the Smart Cricket analysis pipeline through a backend API boundary.

Core idea:

```text
uploaded video
→ API validation
→ Phase 12 inference pipeline
→ structured JSON response
```

Implemented systems:

- `backend/api/app.py`
- `backend/api/routes.py`
- `backend/api/schemas.py`
- `backend/api/services.py`
- `backend/api/validate_api.py`
- `backend/api/tests/test_api.py`

Primary Phase 13 artifacts:

- `ml/artifacts/phase13/sample_api_response.json`
- `ml/artifacts/phase13/api_health.json`
- `ml/artifacts/phase13/api_validation_report.md`

Validation result:

```text
Health endpoint passed: True
Analyze endpoint passed: True
Error handling passed: True
Validation passed: True
```

Important interpretation:

- The API layer calls Phase 12 and does not duplicate ML business logic.
- Phase 13 v1 validates upload transport using known finalized dataset video filenames.
- Arbitrary raw-video preprocessing is intentionally left for later hardening.
- Voice/TTS output remains Phase 14.

Run locally:

```bash
PYTHONPATH=. ml/venv/bin/uvicorn backend.api.app:app --reload
```

---

## 🔊 Phase 14 — Voice Output (Completed)

Phase 14 converts the existing coaching `spoken_feedback` text into audio-ready output.

Core idea:

```text
spoken_feedback
→ TTS service boundary
→ audio artifact
→ frontend audio-ready response
```

Implemented systems:

- `ml/src/voice/voice_config.py`
- `ml/src/voice/tts_service.py`
- `ml/src/voice/validate_voice_output.py`
- `ml/src/voice/tests/test_tts_service.py`

Primary Phase 14 artifacts:

- `ml/artifacts/phase14/sample_voice_output.json`
- `ml/artifacts/phase14/frontend_audio_ready_response.json`
- `ml/artifacts/phase14/voice_health.json`
- `ml/artifacts/phase14/voice_output_report.md`
- `ml/artifacts/phase14/audio_output/sample_spoken_feedback.wav`

Validation result:

```text
Audio generated: True
Audio playable: True
Audio bytes: 213580
Spoken feedback matches analysis: True
Validation passed: True
```

Important interpretation:

- Phase 14 consumes existing feedback; it does not regenerate coaching advice.
- TTS/audio generation is isolated behind a service boundary.
- The local environment could not produce speech frames through macOS `say`, so the provider fell back to a playable WAV audio cue while preserving the exact spoken feedback text in the frontend response.
- A cloud or production TTS provider can replace the local provider later without changing the feedback engine.

---

## 🌐 Website App

The repository includes a polished React website/app shell in `frontend/`.

It provides:

- project intro and creator credit for Abhijai Raghuvanshi
- Supabase-ready login and account creation
- camera recording and video upload workflow
- model analysis submission to the FastAPI `/analyze` endpoint
- side panel for prediction, technique score, shot segment, feedback, and spoken text
- shot history chart showing shot counts and detected segment duration

Run locally:

```bash
cd frontend
npm install
npm run dev
```

Frontend env setup:

```bash
cp frontend/.env.example frontend/.env
```

Then set:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_SUPABASE_URL=https://your-project-ref.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=sb_publishable_your_key_here
```

Supabase schema:

```text
supabase/migrations/202608040001_smart_cricket_app_schema.sql
```

The schema uses authenticated owner-scoped RLS policies for profiles, analysis sessions, and shot timeline events.

---
### 🔹  Why Phase 7 Matters

Cricket shots are motion sequences, not static poses.

Instead of learning isolated posture snapshots, Smart Cricket now learns:
```
stance
→ backswing
→ swing
→ follow-through
```
This establishes the core temporal intelligence layer required for:

* sequence-aware shot classification
* motion understanding
* future real-time cricket analysis
* AI coaching systems

---
## 📂 Project Structure

ml/
├── src/
│   ├── preprocessing/
│   │   ├── extract_pose.py
│   │   ├── batch_extract_pose.py
│   │   ├── inspect_pose_data.py
│   │   ├── clean_pose_data.py
│   │   ├── verify_cleaned_pose_data.py
│   │   ├── normalize_pose_data.py
│   │   ├── align_pose_orientation.py
│   │   └── prepare_sequences.py
│   │
│   ├── features/
│   │   ├── feature_config.py
│   │   ├── geometry_utils.py
│   │   ├── joint_angle_features.py
│   │   ├── posture_features.py
│   │   ├── motion_features.py
│   │   ├── shot_specific_features.py
│   │   ├── feature_builder.py
│   │   ├── build_feature_dataset.py
│   │   ├── validate_feature_dataset.py
│   │   ├── temporal_frame_features.py
│   │   └── verify_temporal_frame_features.py
│   │
│   ├── dataset/
│   │   ├── create_feature_schema.py
│   │   ├── create_label_encoder.py
│   │   ├── build_feature_matrix.py
│   │   ├── create_dataset_splits.py
│   │   ├── validate_final_dataset.py
│   │   └── create_dataset_manifest.py
│   │
│   ├── dataset_temporal/
│   │   ├── create_temporal_feature_schema.py
│   │   ├── build_temporal_feature_tensor.py
│   │   ├── validate_temporal_features.py
│   │   ├── create_temporal_label_encoder.py
│   │   ├── create_temporal_dataset_splits.py
│   │   ├── validate_temporal_dataset.py
│   │   └── create_temporal_dataset_manifest.py
│   └── models/
│       ├── __init__.py
│       ├── model_config.py
│       ├── gru_classifier.py
│       ├── test_gru_shapes.py
│       ├── bilstm_classifier.py
│       ├── test_bilstm_shapes.py
│       ├── model_utils.py
│       └── validate_temporal_architectures.py
│   │
│   └── training/
│       ├── training_config.py
│       ├── reproducibility.py
│       ├── temporal_dataset.py
│       ├── feature_scaler.py
│       ├── trainer.py
│       ├── checkpointing.py
│       ├── metrics.py
│       ├── train_temporal_models.py
│       ├── evaluate_temporal_model.py
│       ├── compare_temporal_models.py
│       └── tests/
│   │
│   └── segmentation/
│       ├── __init__.py
│       ├── motion_energy.py
│       ├── state_machine.py
│       ├── shot_segmenter.py
│       ├── validate_shot_segmentation.py
│       └── tests/
│   │
│   └── scoring/
│       ├── __init__.py
│       ├── score_config.py
│       ├── technique_scoring.py
│       ├── validate_technique_scoring.py
│       └── tests/
│   │
│   └── feedback/
│       ├── __init__.py
│       ├── feedback_schema.py
│       ├── feedback_rules.py
│       ├── feedback_templates.py
│       ├── feedback_engine.py
│       ├── validate_feedback_engine.py
│       └── tests/
│   │
│   └── inference/
│       ├── __init__.py
│       ├── inference_config.py
│       ├── result_schema.py
│       ├── analysis_pipeline.py
│       ├── run_inference.py
│       ├── validate_inference_pipeline.py
│       └── tests/
│   │
│   └── voice/
│       ├── __init__.py
│       ├── voice_config.py
│       ├── tts_service.py
│       ├── validate_voice_output.py
│       └── tests/
│
│
├── data/
│   ├── raw_videos/
│   │   ├── cover_drive/
│   │   ├── pull_shot/
│   │   ├── defensive_shot/
│   │   ├── sweep_shot/
│   │   └── idle/
│   │
│   ├── annotations/
│   │   └── metadata.csv
│   │
│   ├── processed/
│   │   ├── pose_json/
│   │   ├── pose_cleaned/
│   │   ├── pose_normalized/
│   │   ├── pose_aligned/
│   │   ├── pose_sequences/
│   │   └── features/
│   │       └── features.csv
│   │
│   ├── final/
│   │   ├── X.npy
│   │   ├── y.npy
│   │   ├── X_train.npy
│   │   ├── X_val.npy
│   │   ├── X_test.npy
│   │   ├── y_train.npy
│   │   ├── y_val.npy
│   │   ├── y_test.npy
│   │   ├── dataset_index.csv
│   │   ├── train_index.csv
│   │   ├── val_index.csv
│   │   ├── test_index.csv
│   │   ├── feature_schema.json
│   │   ├── label_encoder.pkl
│   │   ├── label_mapping.json
│   │   ├── split_metadata.json
│   │   ├── final_dataset_report.md
│   │   └── dataset_manifest.json
│   │
│   └── final_temporal/
│       ├── X_sequence.npy
│       ├── y_sequence.npy
│       ├── X_train_sequence.npy
│       ├── X_val_sequence.npy
│       ├── X_test_sequence.npy
│       ├── y_train_sequence.npy
│       ├── y_val_sequence.npy
│       ├── y_test_sequence.npy
│       ├── temporal_feature_schema.json
│       ├── temporal_label_mapping.json
│       ├── temporal_label_encoder.pkl
│       ├── temporal_split_metadata.json
│       ├── temporal_dataset_report.md
│       └── temporal_dataset_manifest.json
│
└── docs/  
    ├── phase_6_dataset_finalization_strategy.md  
    └── future phase documentation...


---

## ▶️ How to Run Pipeline

### 1. Batch Pose Extraction

python ml/src/preprocessing/batch_extract_pose.py

---

### 2. Cleaning & Processing

python ml/src/preprocessing/inspect_pose_data.py  
python ml/src/preprocessing/clean_pose_data.py  
python ml/src/preprocessing/normalize_pose_data.py  
python ml/src/preprocessing/align_pose_orientation.py  
python ml/src/preprocessing/prepare_sequences.py  

---

## 🧠 Key Concept

Video Data  
→ Pose Data  
→ Clean Motion Sequences  
→ Biomechanical Features  
→ Machine Learning  

Instead of learning directly from raw pixels, the system learns from structured human movement patterns extracted from cricket batting actions.

---

## 🏏 Temporal ML Architecture Upgrade (Completed)

During Phase 7 planning, an important architectural issue was discovered.

The original Phase 6 dataset produced:

```text
X_train.shape = (56, 32)
```

This rank-2 representation worked for classical ML baselines but was incompatible with:

- GRU
- BiLSTM
- temporal sequence learning

because temporal models require:

```text
[samples, time_steps, feature_dimension]
```

To solve this, the pipeline was redesigned to preserve:

```text
frame-by-frame motion evolution
```

instead of compressing an entire batting shot into a single summarized vector.

Final temporal dataset:

```text
X_sequence.shape = (80, 60, 32)
```

This means:

```text
80 batting shots
→ 60 frames each
→ 32 engineered biomechanical features per frame
```

The redesigned temporal pipeline now includes:

- Per-frame temporal feature extraction  
- Rank-3 temporal tensors  
- Temporal validation systems  
- Sequence-aware dataset splitting  
- GRU/BiLSTM-ready infrastructure  
- Future real-time inference compatibility  

### Tabular Baseline vs Temporal Dataset

The project now maintains two dataset systems:

### 1. Baseline Tabular Dataset

```text
ml/data/final/
```

Purpose:
- Classical ML baselines  
- Engineering comparison  
- Ablation experiments  

Shape:

```text
(80, 32)
```

---

### 2. Temporal Motion Dataset (Primary)

```text
ml/data/final_temporal/
```

Purpose:
- GRU training  
- BiLSTM training  
- Motion intelligence  
- Sequence-aware classification  

Shape:

```text
(80, 60, 32)
```

Phase 8 used:

```text
ml/data/final_temporal/
```

as the official training dataset and selected:

```text
ml/artifacts/phase8/best_model/checkpoint.pt
```

for later temporal-model phases.

Phase 9 now uses the same temporal features for segmentation:

```text
ml/data/final_temporal/X_sequence.npy
→ motion-energy signal
→ state machine
→ one prediction trigger per completed shot
```

---

### Long-Term Vision

Future phases will include:

- advanced motion understanding  
- technique scoring  
- cricket coaching feedback  
- real-time inference  
- AI-assisted batting analysis  

---

## 💡 Project Goal

To build a system that not only detects cricket shots but also:

- Understands technique
- Identifies mistakes
- Provides intelligent feedback
- Builds a future real-time AI cricket coaching assistant
