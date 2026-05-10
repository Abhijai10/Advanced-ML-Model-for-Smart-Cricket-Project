# 🏏 Smart Cricket — Advanced ML Model

## 🚀 Project Overview

Smart Cricket is an AI-powered cricket analytics system designed to analyze batting shots using pose estimation and motion analysis.

Instead of relying on single images, this project processes full video sequences, extracts human pose keypoints, and converts them into structured data for:

- Shot classification  
- Motion understanding  
- Future real-time feedback system  

---

## 📊 Current Progress

The project is being developed in structured phases:

- ✅ Phase 1: Project Architecture & Setup  
- ✅ Phase 2: Pose Pipeline Setup  
- ✅ Phase 2.5: Dataset Building & Annotation  
- ✅ Phase 3: Batch Pose Extraction  
- ✅ Phase 4: Pose Cleaning & Normalization  
- ✅ Phase 5: Feature Engineering & Dataset Validation  

👉 Current Status:

The pipeline now successfully converts raw cricket videos into structured biomechanical feature vectors ready for machine learning.

Current completed outputs:

- Cleaned and normalized pose sequences  
- Fixed-length temporal pose representations  
- 32 engineered biomechanical features  
- Validated feature dataset (features.csv)  
- Balanced 4-class training dataset  

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

## ⚙️ Data Processing Pipeline

Raw Videos  
↓  
Pose Extraction (MediaPipe)  
↓  
Pose JSON Files  
↓  
Cleaning & Validation  
↓  
Normalization  
↓  
Orientation Alignment  
↓  
Fixed-Length Sequences (60 frames)  
↓  
Biomechanical Feature Extraction  
↓  
Validated Feature Dataset (features.csv)  

Each video is transformed into structured biomechanical information containing:

- pose movement patterns  
- joint-angle statistics  
- posture features  
- motion dynamics  
- cricket-specific shot mechanics  

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

## 📂 Project Structure

ml/  
  src/  
    preprocessing/  
      extract_pose.py  
      batch_extract_pose.py  
      inspect_pose_data.py  
      clean_pose_data.py  
      normalize_pose_data.py  
      align_pose_orientation.py  
      prepare_sequences.py  
      verify_cleaned_pose_data.py  

    features/  
      feature_config.py  
      geometry_utils.py  
      joint_angle_features.py  
      posture_features.py  
      motion_features.py  
      shot_specific_features.py  
      feature_builder.py  
      build_feature_dataset.py  
      validate_feature_dataset.py  

  data/  
    raw_videos/  
    annotations/  
      metadata.csv  

    processed/  
      pose_sequences/  
      features/  
        features.csv  

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

- Phase 6: Model Training Pipeline  
- Feature scaling and preprocessing  
- Baseline ML model training  
- Shot classification system  
- Model evaluation and comparison  
- Technique analysis system  
- Feedback generation pipeline  

---

## 💡 Project Goal

To build a system that not only detects cricket shots but also:

- Understands technique  
- Identifies mistakes  
- Provides intelligent feedback  
- Enables real-time coaching assistance  