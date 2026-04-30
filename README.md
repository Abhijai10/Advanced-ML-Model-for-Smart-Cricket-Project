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

👉 Current Status:  
All training videos have been successfully converted into pose JSON format.

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
(Next: Cleaning & Normalization)  

Each video is converted into a JSON file containing:

- video_metadata  
- frame-wise pose data  
- 33 body landmarks per frame (x, y, z, visibility)  

---

## 📂 Project Structure

ml/  
  src/  
    preprocessing/  
      extract_pose.py  
      batch_extract_pose.py  

  data/  
    raw_videos/  
    annotations/  
      metadata.csv  
    processed/  
      pose_json/  

---

## ▶️ How to Run Pose Extraction

Run full batch processing:

python src/preprocessing/batch_extract_pose.py

For testing on a single video:

python src/preprocessing/batch_extract_pose.py --limit 1

---

## 🧠 Key Concept

This project converts:

Video Data → Structured Motion Data → ML Features  

Instead of raw pixels, the model learns from human body movement over time.

---

## 🔜 Next Steps

- Pose Cleaning  
- Normalization  
- Sequence Creation  
- Model Training  
- Real-time Shot Prediction  
- Feedback Generation System  

---

## 💡 Project Goal

To build a system that not only detects cricket shots but also:

- Understands technique  
- Identifies mistakes  
- Provides intelligent feedback  