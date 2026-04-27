# Architecture

This project is designed as a layered AI coaching pipeline. Each layer does one clear job, and the output of one layer becomes the input for the next layer.

## 1. Video Input Layer

This layer receives a batting video from the user (recorded or uploaded).  
Its job is to validate the file format, store the original video safely, and pass the video location to the next step.

## 2. Pose Extraction Layer

This layer reads the video frame by frame and detects body keypoints (pose landmarks), such as shoulders, elbows, hips, knees, and wrists.  
The output is structured pose data over time instead of raw pixels.

## 3. Preprocessing Layer

Raw pose data can be noisy. This layer cleans it by handling missing points, smoothing unstable landmarks, and normalizing coordinates so different camera distances and body sizes are more comparable.

## 4. Feature Engineering Layer

This layer converts cleaned landmarks into useful motion features, such as joint angles, movement speed, bat swing direction, and body balance indicators.  
These features help the model understand cricket technique more clearly.

## 5. Sequence Model Layer

A sequence model analyzes the full time-series motion (not a single frame).  
It learns the complete batting pattern and predicts the most likely shot class for that motion sequence.

## 6. Shot Segmentation Layer

This layer identifies the start and end of a single swing and ensures the system produces exactly one final prediction for that swing.  
It prevents repeated predictions while the same motion is still in progress.

## 7. Technique Scoring Layer

After shot classification, this layer compares the user sequence with ideal or pro-player reference sequences.  
It computes a technique match percentage and highlights where timing, angles, or posture differ.

## 8. Feedback Engine

This layer converts technical differences into readable coaching guidance.  
It detects common mistakes and provides actionable suggestions (for example, stance correction, bat path adjustment, or follow-through improvement).

## 9. API Layer

The backend API exposes endpoints for video upload, inference execution, score retrieval, and feedback delivery.  
It coordinates data flow between storage, ML pipeline modules, and response formatting.

## 10. Future Frontend Integration

A future web interface can connect to the API to upload videos, display final shot prediction, show technique score, and present coaching feedback in a user-friendly dashboard.

## End-to-End Data Flow

1. User uploads batting video to the system.
2. Video Input Layer validates and stores the file.
3. Pose Extraction Layer converts video frames into landmarks.
4. Preprocessing Layer cleans and normalizes landmarks.
5. Feature Engineering Layer creates motion-aware features.
6. Shot Segmentation Layer isolates one complete swing.
7. Sequence Model Layer predicts one final shot label.
8. Technique Scoring Layer computes match percentage vs references.
9. Feedback Engine generates mistake analysis and coaching advice.
10. API Layer returns prediction, score, and feedback (for backend clients now and frontend apps later).
