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
- Cursor AI-assisted development workflow

---

## 📊 Current Progress

The project is being developed in structured engineering phases:

- ✅ Phase 1: Project Architecture & Setup  
- ✅ Phase 2: Pose Pipeline Setup  
- ✅ Phase 2.5: Dataset Building & Annotation  
- ✅ Phase 3: Batch Pose Extraction  
- ✅ Phase 4: Pose Cleaning & Normalization  
- ✅ Phase 5: Feature Engineering  
- ✅ Phase 6: Dataset Finalization & ML Dataset Infrastructure  

---

### ✅ Current System Capabilities

The pipeline now successfully converts raw cricket batting videos into a fully validated and reproducible ML-ready dataset.

Current completed outputs:

- Cleaned and normalized pose sequences  
- Orientation-aligned pose data  
- Fixed-length temporal motion sequences (60 frames)  
- 32 engineered biomechanical features  
- Encoded shot labels  
- Finalized train/validation/test splits  
- ML-ready NumPy datasets  
- Dataset manifests and validation reports  
- Fully reproducible dataset infrastructure  

---

### 📦 Final Dataset Status

- Total ML samples: 80  
- Number of features: 32  
- Classes: 4 balanced cricket shot categories  
- Train split: 56 samples  
- Validation split: 12 samples  
- Test split: 12 samples  

The project now contains a fully packaged machine-learning dataset ready for model training and evaluation.

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
Cleaning & Validation  
↓  
Pose Normalization  
↓  
Orientation Alignment  
↓  
Fixed-Length Temporal Sequences (60 frames)  
↓  
Biomechanical Feature Engineering  
↓  
Feature Dataset (features.csv)  
↓  
Feature Schema Generation  
↓  
Label Encoding  
↓  
Feature Matrix Construction  
↓  
Train / Validation / Test Splitting  
↓  
Dataset Validation & Packaging  
↓  
ML-Ready Dataset Infrastructure  

---

### 🧠 Final ML Dataset Artifacts

The finalized dataset layer now includes:

- `X_train.npy`
- `X_val.npy`
- `X_test.npy`
- `y_train.npy`
- `y_val.npy`
- `y_test.npy`
- `feature_schema.json`
- `label_mapping.json`
- `split_metadata.json`
- `dataset_manifest.json`
- `final_dataset_report.md`

This creates a fully reproducible and training-ready ML dataset system.

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

The system extracts cricket-specific motion and posture information from each batting sequence and converts it into a fixed-size numerical feature vector.

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

## 🔹 Feature Dataset

Final generated dataset:

- 80 processed samples  
- 4 balanced cricket shot classes  
- 32 biomechanical features per sample  
- ML-ready tabular dataset (features.csv)  

The dataset was validated for:
- NaN values  
- infinite values  
- feature consistency  
- dataset integrity  

### Current Dataset State

- 80 validated training samples  
- 4 balanced shot classes  
- 60-frame temporal pose sequences  
- 32 engineered biomechanical features  
- ML-ready tabular dataset for training  

---

## 🧠 Phase 6 — Dataset Finalization (Completed)

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
│   │   └── validate_feature_dataset.py  
│   │
│   └── dataset/  
│       ├── create_feature_schema.py  
│       ├── create_label_encoder.py  
│       ├── build_feature_matrix.py  
│       ├── create_dataset_splits.py  
│       ├── validate_final_dataset.py  
│       └── create_dataset_manifest.py  
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
│   └── final/  
│       ├── X.npy  
│       ├── y.npy  
│       ├── X_train.npy  
│       ├── X_val.npy  
│       ├── X_test.npy  
│       ├── y_train.npy  
│       ├── y_val.npy  
│       ├── y_test.npy  
│       ├── dataset_index.csv  
│       ├── train_index.csv  
│       ├── val_index.csv  
│       ├── test_index.csv  
│       ├── feature_schema.json  
│       ├── label_encoder.pkl  
│       ├── label_mapping.json  
│       ├── split_metadata.json  
│       ├── final_dataset_report.md  
│       └── dataset_manifest.json  
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

## 🔜 Next Steps

### Phase 7 — Baseline Model Building

Upcoming work includes:

- Logistic Regression baseline
- Random Forest baseline
- Support Vector Machine (SVM)
- Model evaluation pipelines
- Confusion matrix analysis
- Accuracy / Precision / Recall / F1-score evaluation
- Baseline model comparison
- Model artifact saving
- Future inference pipeline integration

---

### Long-Term Vision

Future phases will include:

- sequence models (GRU/LSTM)
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
- Build a future real-time AI cricket coaching assistant