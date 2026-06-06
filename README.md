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

Current development is now focused on:

```text
Temporal model training & evaluation
```
using :
```
GRU / BiLSTM temporal architectures
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
Phase 8 Training & Evaluation

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
This ensures the models are fully compatible with the finalized temporal dataset and ready for Phase 8 training.

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

Phase 8 will use:

```text
ml/data/final_temporal/
```

as the official training dataset.

---

### Long-Term Vision

Future phases will include:

- temporal model training & evaluation  
- GRU vs BiLSTM comparison  
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