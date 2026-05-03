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

👉 Current Status:  
All pose data has been processed into clean, normalized, aligned, and fixed-length sequences ready for ML.

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
Alignment  
↓  
Fixed-Length Sequences (60 frames)  

Each video is converted into structured data containing:

- frame-wise pose data  
- 33 body landmarks per frame (x, y, z, visibility)  

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

  data/  
    raw_videos/  
    annotations/  
      metadata.csv  
    processed/  
      pose_sequences/  

---

## ▶️ How to Run Pipeline

### 1. Batch Pose Extraction

python src/preprocessing/batch_extract_pose.py

---

### 2. Cleaning & Processing

python ml/src/preprocessing/inspect_pose_data.py  
python ml/src/preprocessing/clean_pose_data.py  
python ml/src/preprocessing/normalize_pose_data.py  
python ml/src/preprocessing/align_pose_orientation.py  
python ml/src/preprocessing/prepare_sequences.py  

---

## 🧠 Key Concept

Video Data → Pose Data → Clean Sequences → ML Features (Next Phase)

Instead of raw pixels, the model learns from human body movement over time.

---

## 🔜 Next Steps

- Phase 5: Feature Engineering  
- Feature extraction (angles, posture, motion)  
- Model training  
- Shot classification  
- Technique analysis  
- Feedback generation system  

---

## 💡 Project Goal

To build a system that not only detects cricket shots but also:

- Understands technique  
- Identifies mistakes  
- Provides intelligent feedback  
- Enables real-time coaching assistance  