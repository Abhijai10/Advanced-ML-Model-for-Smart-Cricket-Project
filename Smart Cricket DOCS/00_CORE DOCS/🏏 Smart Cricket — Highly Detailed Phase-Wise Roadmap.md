

---
# **1. Project Identity**

## **Project Name**

Smart Cricket — Advanced ML Model

## **Project Type**

AI-based cricket shot analysis and coaching system.

## **Core Objective**

Build an AI system that can analyze a cricket batting video, understand the complete shot motion, classify the shot, evaluate technique, detect mistakes, and generate explainable coaching feedback.

This project is not just a shot classifier.

It is designed as:

```text
video-based cricket motion understanding
→ biomechanical analysis
→ explainable feedback
→ future AI coaching assistant
```

---

# **2. Core System Vision**

The long-term system should answer four main questions for every completed batting action:

```text
1. What shot was played?
2. How confident is the model?
3. How good was the technique?
4. What should the player improve?
```

The final system should support:

```text
Raw video
→ Pose extraction
→ Pose preprocessing
→ Feature engineering
→ Shot classification
→ Technique scoring
→ Feedback generation
→ API response
→ Future voice output
```

---

# **3. Core Engineering Principles**

## **3.1 Analyze Full Motion, Not One Frame**

Cricket shots are dynamic actions.

A single frame cannot capture:

```text
backswing
weight transfer
shoulder rotation
knee bend
elbow extension
follow-through
timing
```

So this project uses sequence-based motion understanding.

---

## **3.2 Use Pose Data Instead of Raw Pixels**

Raw video contains too much noise:

```text
background
lighting
clothes
camera distance
room setup
body size
```

Pose landmarks reduce the problem to human body movement.

This makes the system:

```text
lighter
more interpretable
easier to debug
better for small datasets
better for feedback generation
```

---

## **3.3 Use Hybrid AI**

The system should not rely only on black-box ML.

Final philosophy:

```text
ML model → detects shot type
Biomechanical rules/templates → explain technique and mistakes
```

This is important because coaching feedback should be explainable.

---

## **3.4 Build Phase by Phase**

This project must not jump directly to model training.

Correct flow:

```text
architecture
→ dataset
→ pose extraction
→ preprocessing
→ features
→ dataset finalization
→ model
→ training
→ segmentation
→ scoring
→ feedback
→ inference
→ API
→ voice
```

---

# **4. Full Locked Project Roadmap**

```text
Phase 1 — Project Architecture
Phase 2 — Environment + Base Setup
Phase 2.5 — Dataset Creation
Phase 3 — Batch Pose Extraction
Phase 4 — Pose Cleaning & Normalization
Phase 5 — Feature Engineering
Phase 6 — Dataset Finalization
Phase 7 — Model Building
Phase 8 — Model Training & Evaluation
Phase 9 — Shot Segmentation
Phase 10 — Technique Scoring System
Phase 11 — Feedback Engine
Phase 12 — Inference Pipeline
Phase 13 — API Integration
Phase 14 — Voice Output
```

---

# **Phase 1 — Project Architecture**

## **🎯 Goal**

Create the foundation of the Smart Cricket Advanced ML project before writing serious ML logic.

This phase answers:

```text
What are we building?
Where will each part live?
How will the system grow later?
```

## **Input → Output**

```text
Input:
Project idea

Output:
Structured project repository
Architecture documents
Dataset format plan
README
Config structure
GitHub foundation
```

## **What This Phase Builds**

This phase establishes:

```text
ml/
backend/
docs/
data/
config.py
requirements.txt
README.md
.gitignore
```

It also defines the major system layers:

```text
pose extraction
preprocessing
feature engineering
training
feedback
inference
API
```

## **Key Concepts**

### **Architecture-first development**

Do not start with random scripts.

A serious ML system needs structure before coding.

### **Separation of concerns**

Each folder should have one purpose.

Example:

```text
preprocessing/ → data cleaning and normalization
features/ → biomechanical feature generation
training/ → model training scripts
feedback/ → coaching logic
```

### **Central configuration**

Paths, labels, sequence length, and constants should be stored centrally instead of being hardcoded repeatedly.

## **Key Engineering Decisions**

```text
Do not train model yet.
Do not collect huge dataset yet.
Create structure first.
Use micro-prompts for Cursor.
Keep repo clean and modular.
```

## **Deliverables**

```text
README.md
docs/architecture.md
docs/dataset_format.md
ml/src/config.py
requirements.txt
.gitignore
initial folder structure
first meaningful Git commit
```

## **Success Criteria**

Phase 1 is complete when:

```text
project structure is clean
README explains project clearly
architecture is documented
dataset plan exists
GitHub repo has first meaningful commit
```

## **Future Impact**

Every later phase depends on this structure.

Without Phase 1, later code becomes messy and difficult to debug.

---

# **Environment + Base Setup / Pose Pipeline Setup**

## **🎯 Goal**

Set up the working ML environment and build the first basic pose extraction pipeline.

This phase turns the project from:

```text
planned architecture
```

into:

```text
working computer vision pipeline
```

## **Input → Output**

```text
Input:
One cricket video

Output:
Pose JSON file
Basic pose sequence data
Initial preprocessing output
```

## **What This Phase Builds**

This phase creates the first technical pipeline:

```text
video
→ OpenCV frame reading
→ MediaPipe pose detection
→ frame-wise landmarks
→ JSON output
```

Each frame stores:

```text
frame_index
timestamp
33 pose landmarks
x, y, z, visibility
```

## **Key Concepts**

### **Pose estimation**

Pose estimation detects human body landmarks from video frames.

For this project, it converts cricket videos into body movement data.

### **MediaPipe Pose**

MediaPipe is used as the pretrained pose extraction system.

Important distinction:

```text
MediaPipe Pose = pretrained body landmark detector
Smart Cricket Model = future custom cricket shot classifier
```

### **JSON as intermediate representation**

JSON is readable and inspectable.

This makes it useful before training.

### **Visibility score**

Visibility tells how reliable each landmark is.

Low visibility may indicate:

```text
occlusion
blur
bad lighting
body part outside frame
```

## **Key Engineering Decisions**

```text
Use pose landmarks instead of raw pixels.
Use MediaPipe for first version.
Use JSON first because it is debuggable.
Do not train model yet.
```

## **Deliverables**

```text
extract_pose.py
basic pose JSON output
requirements installed
MediaPipe working
sample video processed
README updated
```

## **Success Criteria**

Phase 2 is complete when:

```text
one video can be processed successfully
pose landmarks are saved
JSON structure is understandable
skeleton visualization or inspection confirms extraction is working
```

## **Future Impact**

Phase 2 enables all downstream work.

Without pose extraction, there is no preprocessing, feature engineering, model training, scoring, or feedback.

---

# **Phase 2.5 — Dataset Creation**

## **🎯 Goal**

Create a structured cricket shot dataset that the ML pipeline can process automatically.

This phase transforms:

```text
random collected videos
```

into:

```text
organized labeled dataset
```

## **Input → Output**

```text
Input:
Raw cricket shot videos

Output:
Organized folders
metadata.csv
shot labels
quality labels
use_for_v1 filtering
```

## **Dataset Philosophy**

The dataset is not just videos.

A real ML dataset contains:

```text
videos
labels
metadata
file paths
quality information
person identity
usage flags
```

## **Dataset Strategy**

The project uses a hybrid dataset philosophy.

### **Real-user / normal-player videos**

Used for:

```text
training shot recognition
real-world robustness
learning imperfect human movement
```

### **Pro-reference videos**

Used later for:

```text
ideal templates
technique scoring
biomechanical reference
feedback comparison
```

Important:

```text
Your videos = reality
Pro videos = ideal reference
```

## **Current Shot Classes**

```text
cover_drive
pull_shot
defensive_shot
sweep_shot
```

## **Quality Labels**

```text
good
average
bad
```

These are simple labels.

Detailed biomechanical mistake labels are not required at this stage because manually labeling elbow collapse, head misalignment, or balance issues without expert knowledge can create noisy labels.

## **Metadata Fields**

```text
video_id
file_name
relative_path
shot_label
quality
person_id
use_for_v1
```

## **Key Concepts**

### **Metadata as source of truth**

Folder structure is not enough.

Metadata tells scripts:

```text
which video to use
where it is
what label it has
who performed it
whether it belongs to V1
```

### **Simple labels first**

The system should start with:

```text
shot_label + quality
```

Detailed mistake detection should come later from pose-based geometry and rules.

### **Person-aware splitting**

Future evaluation should split by person where possible.

This prevents fake accuracy caused by the same player appearing in both train and test.

## **Key Engineering Decisions**

```text
Use 4 biomechanically distinct classes.
Exclude idle from V1 classifier.
Keep pro reference separate from training metadata.
Use metadata.csv instead of manual file guessing.
Avoid detailed mistake labels early.
```

## **Deliverables**

```text
data/raw_videos/
data/pro_reference/
data/annotations/metadata.csv
create_metadata.py
organized shot folders
80 V1 training samples
idle clips marked use_for_v1 = no
```

## **Success Criteria**

Phase 2.5 is complete when:

```text
all videos are organized
metadata.csv exists
all V1 samples are marked correctly
idle clips are excluded from V1
shot labels are consistent
quality labels are assigned
```

## **Future Impact**

This phase enables metadata-driven automation in Phase 3.

If metadata is wrong, every future phase becomes unreliable.

---

# **Phase 3 — Batch Pose Extraction**

## **🎯 Goal**

Convert all selected dataset videos into structured pose JSON files automatically.

This phase transforms:

```text
80 selected videos
```

into:

```text
80 pose JSON files
```

## **Input → Output**

```text
Input:
data/raw_videos/
metadata.csv

Output:
data/processed/pose_json/
```

## **What This Phase Builds**

A batch processing script that:

```text
reads metadata.csv
filters use_for_v1 = yes
loops through videos
calls single-video extractor
saves pose JSON
skips existing outputs
logs failures
```

## **Key Concepts**

### **Batch processing**

Instead of manually processing one video at a time, one script processes the full dataset.

### **Metadata-driven automation**

The script should not blindly scan folders.

It should follow metadata.

### **Dry run**

Dry run simulates processing without executing heavy operations.

It verifies:

```text
input paths
output paths
selected files
missing files
already processed files
```

### **Idempotency**

If output already exists, skip it.

This makes rerunning safe.

## **Key Engineering Decisions**

```text
Create batch_extract_pose.py instead of modifying extract_pose.py heavily.
Reuse existing extraction functions.
Use metadata.csv as source of truth.
Add dry-run before full extraction.
Add failure log.
Skip existing outputs.
```

## **Deliverables**

```text
batch_extract_pose.py
pose_json/ outputs
batch_failures.csv if needed
README update
verified JSON count
```

## **Success Criteria**

Phase 3 is complete when:

```text
80 V1 videos produce 80 pose JSON files
no unwanted extra files remain
failure count is zero or understood
output count matches metadata expectation
```

## **Future Impact**

Phase 4 depends directly on these pose JSON files.

Without clean pose JSON, preprocessing cannot begin.

---

# **Phase 4 — Pose Cleaning & Normalization**

## **🎯 Goal**

Convert raw pose JSON files into clean, normalized, aligned, fixed-length pose sequences.

This phase transforms:

```text
raw pose JSON
```

into:

```text
ML-ready pose_sequences
```

## **Input → Output**

```text
Input:
data/processed/pose_json/

Output:
data/processed/pose_sequences/
80 files
60 frames per file
```

## **What This Phase Builds**

This phase builds the preprocessing pipeline:

```text
inspect
clean
verify
normalize
align
prepare sequences
```

## **Step 4.1 — Inspect Pose Data**

### **Purpose**

Understand dataset quality before modifying anything.

### **Checks**

```text
number of files
frame counts
missing landmarks
low visibility frames
shortest sequence
longest sequence
major issue files
```

### **Why It Matters**

Cleaning should be data-driven, not guessed.

---

## **Step 4.2 — Clean Pose Data**

### **Purpose**

Remove clearly invalid frames.

### **Removes**

```text
missing landmarks
empty landmarks
very low visibility frames
```

### **Philosophy**

Use conservative cleaning.

Do not remove useful motion data unnecessarily.

---

## **Step 4.3 — Verify Cleaned Data**

### **Purpose**

Ensure cleaned JSON files are structurally safe.

### **Checks**

```text
valid JSON
frames exist
landmarks exist
x/y/z numeric
visibility valid
no empty sequences
```

---

## **Step 4.4 — Normalize Pose Data**

### **Purpose**

Make different players and camera distances comparable.

### **Method**

```text
center using hip midpoint
scale using torso length
```

### **Why It Matters**

Without normalization, the model may learn:

```text
body size
camera distance
screen position
```

instead of cricket movement.

---

## **Step 4.5 — Align Orientation**

### **Purpose**

Reduce small rotational differences.

### **Method**

```text
use shoulder line angle
rotate x/y coordinates
preserve z and visibility
```

### **Important Limitation**

Alignment reduces small tilt.

It does not fully solve side-view vs front-view camera perspective.

---

## **Step 4.6 — Prepare Fixed-Length Sequences**

### **Purpose**

Create consistent temporal input length.

### **Output**

```text
60 frames per sample
```

### **Method**

```text
uniform downsampling for longer clips
frame duplication for shorter clips
```

## **Key Concepts**

```text
data inspection
conservative cleaning
pose validation
scale invariance
hip-centered coordinates
torso scaling
orientation alignment
fixed-length sequences
data lineage
```

## **Key Engineering Decisions**

```text
Use conservative cleaning.
Use hip midpoint for centering.
Use torso length for scaling.
Use shoulder angle for alignment.
Use 60-frame sequences.
Keep strict filename suffixes.
```

## **Deliverables**

```text
inspect_pose_data.py
clean_pose_data.py
verify_cleaned_pose_data.py
normalize_pose_data.py
align_pose_orientation.py
prepare_sequences.py
pose_cleaned/
pose_normalized/
pose_aligned/
pose_sequences/
```

## **Success Criteria**

Phase 4 is complete when:

```text
80 sequence files exist
each file has exactly 60 frames
JSON structure is valid
normalization completed
alignment completed
outputs are verified
```

## **Future Impact**

Phase 5 depends entirely on these 60-frame sequences.

Bad Phase 4 leads to:

```text
bad features
bad model
bad feedback
```

Strong Phase 4 enables stable feature engineering.

---

# **Phase 5 — Feature Engineering**

## **🎯 Goal**

Convert 60-frame pose sequences into structured biomechanical features.

This phase transforms:

```text
pose_sequences
```

into:

```text
32-feature biomechanical representation
```

## **Input → Output**

```text
Input:
data/processed/pose_sequences/

Output:
feature vectors / feature dataset
```

## **Feature Engineering Philosophy**

The system uses curated features, not every possible feature.

Why?

```text
dataset is small
too many features cause overfitting
redundant features add noise
interpretability is important
feedback requires meaningful features
```

## **Final Feature Set**

Total:

```text
32 features
```

Categories:

```text
8 Joint Angle Features
8 Posture Features
8 Motion Features
8 Shot-Specific Features
```

---

## **5.1 — Feature Definition**

### **Purpose**

Decide exactly what the model should learn.

### **Output**

Locked 32-feature list.

---

## **Joint Angle Features**

```text
lead_elbow_angle_mean
lead_elbow_angle_min
trail_elbow_angle_mean
lead_knee_angle_mean
lead_knee_angle_min
trail_knee_angle_mean
shoulder_rotation_angle_mean
hip_rotation_angle_mean
```

These capture:

```text
arm structure
knee bend
body rotation
shot mechanics
```

---

## **Posture Features**

```text
trunk_lean_mean
trunk_lean_max
head_stability
head_over_base_offset
shoulder_hip_separation_mean
stance_width_mean
body_center_shift_x
body_center_shift_y
```

These capture:

```text
balance
alignment
body stability
weight positioning
```

---

## **Motion Features**

```text
lead_wrist_velocity_mean
lead_wrist_velocity_max
trail_wrist_velocity_mean
trail_wrist_velocity_max
body_center_velocity_mean
body_center_velocity_max
shoulder_rotation_velocity_mean
motion_energy_total
```

These capture:

```text
speed
timing
movement intensity
rotational dynamics
```

---

## **Shot-Specific Features**

```text
front_foot_commitment
back_foot_loading
follow_through_height
follow_through_extension
lead_elbow_extension_change
lead_knee_flexion_change
head_to_lead_knee_alignment
weight_transfer_score
```

These capture cricket-specific mechanics.

---

## **5.2 — Feature Blueprint**

### **Purpose**

Create configuration for all feature groups.

### **Deliverables**

```text
feature_config.py
feature group definitions
landmark index mappings
feature name registry
```

---

## **5.3 — Geometry Helpers**

### **Purpose**

Implement reusable math functions.

### **Examples**

```text
distance
angle between joints
velocity
mean
min
max
safe division
frame-wise displacement
```

---

## **5.4 — Joint Angle Features**

### **Purpose**

Calculate elbow, knee, shoulder, and hip rotation features.

---

## **5.5 — Posture Features**

### **Purpose**

Calculate trunk lean, head stability, stance width, body center movement, and shoulder-hip separation.

---

## **5.6 — Motion Dynamics**

### **Purpose**

Calculate velocities, movement energy, wrist speed, and body center motion.

---

## **5.7 — Shot-Specific Features**

### **Purpose**

Calculate cricket-specific signals like front-foot commitment, back-foot loading, follow-through, and weight transfer.

---

## **5.8 — Feature Builder Pipeline**

### **Purpose**

Combine all feature groups into one consistent feature vector per sample.

---

## **5.9 — Feature Dataset Creation**

### **Purpose**

Create a tabular ML-ready dataset.

Expected output:

```text
features.csv
or
feature_dataset.pkl / npy
```

---

## **5.10 — Feature Validation**

### **Purpose**

Verify feature consistency.

Checks:

```text
no missing values
all samples have 32 features
feature names match config
all values numeric
labels attached correctly
```

## **Key Concepts**

```text
biomechanical features
feature selection
feature redundancy
feature interpretability
small dataset constraints
motion statistics
posture analysis
```

## **Key Engineering Decisions**

```text
Use 32 curated features.
Avoid abstract black-box scores early.
Use measurable pose-derived features.
Keep feature names locked.
Validate every feature before training.
```

## **Deliverables**

```text
feature_config.py
geometry_helpers.py
joint_angle_features.py
posture_features.py
motion_features.py
shot_specific_features.py
build_features.py
feature_dataset
feature validation report
```

## **Success Criteria**

Phase 5 is complete when:

```text
all 80 samples have feature vectors
each feature vector has exactly 32 values
feature names are consistent
no NaN/invalid values exist
features are linked to labels
dataset is ready for Phase 6
```

## **Future Impact**

Phase 5 determines the quality of model input.

Good features make model training easier, more interpretable, and more useful for feedback.

---

# **Phase 6 — Dataset Finalization**

## **🎯 Goal**

Convert engineered features into final training-ready datasets.

This phase transforms:

```text
feature outputs
```

into:

```text
final ML dataset with labels and splits
```

## **Input → Output**

```text
Input:
feature dataset
metadata.csv
labels

Output:
train/validation/test datasets
feature arrays
label arrays
dataset reports
```

## **What This Phase Builds**

This phase prepares the final dataset used by models.

It includes:

```text
feature-label merging
split creation
label encoding
feature scaling if required
dataset serialization
final validation
```

## **Key Concepts**

### **Feature-label alignment**

Every feature row must correctly match the original video label.

### **Train/validation/test split**

Model evaluation requires separation between training and evaluation samples.

### **Person-aware splitting**

Where possible, split by `person_id` to avoid leakage.

### **Label encoding**

Shot labels must be converted from strings to numerical IDs.

Example:

```text
cover_drive → 0
pull_shot → 1
defensive_shot → 2
sweep_shot → 3
```

### **Dataset serialization**

Final datasets may be saved as:

```text
CSV
NumPy arrays
Pickle files
Torch dataset files
```

## **Key Engineering Decisions**

```text
Do not train directly from raw feature scripts.
Create stable finalized dataset artifacts.
Use reproducible split logic.
Preserve metadata references.
Validate all shapes before model building.
```

## **Deliverables**

```text
create_feature_dataset.py
split_dataset.py
label_encoder.py
feature_dataset.csv
X_train.npy
y_train.npy
X_val.npy
y_val.npy
X_test.npy
y_test.npy
dataset_summary.json
```

## **Success Criteria**

Phase 6 is complete when:

```text
features and labels are aligned
splits are created
label mapping is saved
all shapes are verified
no data leakage is obvious
dataset can be loaded by model scripts
```

## **Future Impact**

Phase 7 model building depends on stable input shapes and labels from this phase.

---

# **Phase 7 — Model Building**

## **🎯 Goal**

Build the first temporal model architecture for cricket shot classification.

This phase transforms:

```text
training-ready dataset
```

into:

```text
trainable sequence model
```

## **Input → Output**

```text
Input:
X_train, y_train
feature vectors / sequences

Output:
model architecture
PyTorch model class
configurable model components
```

## **Model Philosophy**

The model should be:

```text
simple enough to debug
strong enough to learn temporal patterns
lightweight enough for future inference
```

## **Initial Model Direction**

Recommended first models:

```text
GRU
BiLSTM
```

## **Why GRU/BiLSTM?**

Cricket shots are temporal.

The model must understand movement over time, not static pose.

GRU/BiLSTM can learn:

```text
early stance
backswing
swing
follow-through
motion progression
```

## **Possible Architectures**

### **Version 1**

```text
Input features
→ GRU/BiLSTM
→ Dense layer
→ Shot class logits
```

### **Version 2**

```text
Input features
→ Temporal encoder
→ Shot classification head
→ Quality prediction head
```

### **Version 3**

```text
Input features
→ Temporal encoder
→ Shot classification
→ Mistake prediction
→ Technique quality estimation
```

## **Key Concepts**

```text
sequence modeling
hidden states
temporal encoding
classification heads
overfitting control
dropout
model configuration
```

## **Key Engineering Decisions**

```text
Do not start with transformers.
Do not overbuild multi-head model immediately.
Build baseline first.
Keep architecture modular.
Allow future upgrades.
```

## **Deliverables**

```text
models/gru_classifier.py
models/bilstm_classifier.py
model_config.py
model initialization tests
shape validation
```

## **Success Criteria**

Phase 7 is complete when:

```text
model accepts input with correct shape
forward pass works
output shape matches number of shot classes
model can be trained by a training script
```

## **Future Impact**

Phase 8 depends on this model for actual training and evaluation.

---

# **Phase 8 — Model Training & Evaluation**

## **🎯 Goal**

Train the temporal shot classifier and evaluate its performance.

This phase transforms:

```text
trainable model + dataset
```

into:

```text
trained model + evaluation report
```

## **Input → Output**

```text
Input:
model architecture
training dataset
validation dataset

Output:
trained model checkpoint
metrics
confusion matrix
evaluation report
```

## **What This Phase Builds**

Training pipeline:

```text
load dataset
initialize model
train epochs
track loss
validate model
save checkpoint
evaluate results
```

## **Evaluation Metrics**

Use:

```text
accuracy
precision
recall
F1 score
confusion matrix
per-class accuracy
training loss
validation loss
```

## **Why Confusion Matrix Matters**

Accuracy alone is not enough.

The confusion matrix tells:

```text
which shots are confused
which class needs more data
which features may be weak
```

Example:

```text
cover_drive confused with defensive_shot
pull_shot classified correctly
sweep_shot underperforming
```

## **Key Concepts**

```text
cross-entropy loss
overfitting
validation split
class imbalance
generalization
metric interpretation
checkpointing
```

## **Key Engineering Decisions**

```text
Train baseline before advanced models.
Do not judge project by first accuracy only.
Use confusion matrix to guide improvements.
Keep training reproducible.
Save model checkpoints.
```

## **Deliverables**

```text
train_model.py
evaluate_model.py
metrics_report.json
confusion_matrix.png
model_checkpoint.pt
training_history.json
```

## **Success Criteria**

Phase 8 is complete when:

```text
training runs end-to-end
model produces predictions
metrics are generated
confusion matrix is available
model checkpoint is saved
major failure cases are understood
```

## **Future Impact**

The trained classifier becomes the recognition core for inference, segmentation, scoring, and feedback.

---

# **Phase 9 — Shot Segmentation**

## **🎯 Goal**

Ensure that one batting motion produces one final prediction.

This phase solves the earlier problem:

```text
multiple predictions during one shot
```

## **Input → Output**

```text
Input:
pose sequence or live pose stream

Output:
detected shot segment
one final prediction trigger
```

## **Core Problem**

A naive frame-by-frame classifier may predict:

```text
cover_drive
defensive_shot
pull_shot
cover_drive
```

during one swing.

This is wrong.

The system should output:

```text
one completed motion → one final shot prediction
```

## **Segmentation Philosophy**

Prediction should happen after the complete motion is observed.

Not every frame.

## **Planned State Machine**

```text
idle
preparation
backswing
swing
follow_through
completed
cooldown
```

## **Motion Signals**

Segmentation can use:

```text
wrist velocity
shoulder rotation velocity
body center movement
motion energy
pose displacement
follow-through stabilization
```

## **Cooldown Logic**

After a prediction:

```text
ignore new predictions for a short period
```

unless a new clear motion starts.

## **Key Concepts**

```text
state machines
motion energy
temporal smoothing
event detection
cooldown
prediction gating
```

## **Key Engineering Decisions**

```text
Do not classify continuously without control.
Use explainable state machine first.
Use motion thresholds before advanced segmentation models.
Make debug output visible.
```

## **Deliverables**

```text
shot_segmenter.py
motion_energy.py
state_machine.py
segmentation_debug_report
cooldown logic
single-shot prediction tests
```

## **Success Criteria**

Phase 9 is complete when:

```text
one clip gives one final prediction
repeated predictions are reduced
state transitions are explainable
motion start/end can be inspected
```

## **Future Impact**

This phase is critical for real-time use.

Without segmentation, the final app will feel unstable and unprofessional.

---

# **Phase 10 — Technique Scoring System**

## **🎯 Goal**

Create a technique match score that compares user movement against ideal cricket movement.

This phase transforms:

```text
features + predicted shot
```

into:

```text
technique score
```

## **Important Distinction**

```text
Shot confidence ≠ technique score
```

Shot confidence answers:

```text
What shot does the model think this is?
```

Technique score answers:

```text
How well was the shot executed?
```

## **Input → Output**

```text
Input:
predicted shot
engineered features
ideal templates

Output:
technique_match_score
component scores
deviation summary
```

## **Template Strategy**

Ideal templates may come from:

```text
pro reference clips
best user clips
high-quality labeled examples
```

Templates store expected ranges for:

```text
head position
knee bend
elbow angle
trunk lean
follow-through
weight transfer
shoulder/hip rotation
```

## **Possible Scoring Components**

```text
head_stability_score
front_foot_commitment_score
lead_elbow_score
knee_bend_score
weight_transfer_score
follow_through_score
rotation_score
balance_score
```

## **Scoring Philosophy**

The score should be:

```text
interpretable
not random
not just model probability
based on measurable features
```

## **Key Concepts**

```text
template matching
weighted scoring
feature deviation
normalization
biomechanical comparison
```

## **Key Engineering Decisions**

```text
Keep scoring rule-based initially.
Use feature deviations from ideal ranges.
Return component scores, not only one total score.
Do not pretend classifier confidence is technique quality.
```

## **Deliverables**

```text
technique_scoring.py
ideal_template_schema.json
score_config.py
component score functions
technique_score_report.json
```

## **Success Criteria**

Phase 10 is complete when:

```text
system returns technique score from 0–100
score is based on measurable features
component scores are available
score explanation can be generated
```

## **Future Impact**

The feedback engine depends heavily on this phase.

Without scoring, feedback becomes generic.

---

# **Phase 11 — Feedback Engine**

## **🎯 Goal**

Generate human-readable coaching feedback from detected biomechanical issues.

This phase transforms:

```text
feature deviations + score components
```

into:

```text
coaching feedback
```

## **Input → Output**

```text
Input:
predicted shot
technique score
feature values
template deviations

Output:
mistake list
coaching tips
detailed feedback
spoken feedback text
```

## **Feedback Philosophy**

The feedback engine should behave like a coach.

It should not simply say:

```text
bad shot
```

It should explain:

```text
what went wrong
why it matters
how to improve
```

## **Example Feedback Rules**

```text
If head_over_base_offset is high:
"Keep your head more stable over your base."

If lead_elbow_angle_min is too low:
"Try to maintain a stronger lead elbow through the shot."

If follow_through_extension is weak:
"Complete your follow-through more fully."

If weight_transfer_score is low:
"Transfer your body weight forward during the shot."
```

## **Feedback Output Layers**

The system should generate:

```text
detected_issues
coaching_tips
detailed_feedback
spoken_feedback
debug_metadata
```

## **Key Concepts**

```text
rule-based AI
explainable feedback
biomechanical thresholds
natural language coaching
template deviation interpretation
```

## **Key Engineering Decisions**

```text
Do not rely only on ML for feedback.
Use measurable features.
Keep rules editable.
Generate short and detailed outputs separately.
Make output TTS-friendly.
```

## **Deliverables**

```text
feedback_engine.py
feedback_rules.py
feedback_templates.py
feedback_schema.py
sample_feedback_outputs.json
```

## **Success Criteria**

Phase 11 is complete when:

```text
system produces meaningful feedback
feedback is linked to features
tips are readable
spoken feedback string exists
debug info explains why feedback was produced
```

## **Future Impact**

This is the phase that makes Smart Cricket feel like a coach instead of just a classifier.

---

# **Phase 12 — Inference Pipeline**

## **🎯 Goal**

Combine all modules into one end-to-end offline analysis pipeline.

This phase transforms:

```text
single input video
```

into:

```text
complete analysis result
```

## **Input → Output**

```text
Input:
one cricket batting video

Output:
structured JSON result
```

## **Full Pipeline**

```text
video
→ pose extraction
→ preprocessing
→ feature engineering
→ shot classification
→ segmentation/gating
→ technique scoring
→ feedback generation
→ final JSON
```

## **Expected Output JSON**

```json
{
  "predicted_shot": "cover_drive",
  "shot_confidence": 0.91,
  "technique_match_score": 78,
  "detected_issues": [],
  "coaching_tips": [],
  "detailed_feedback": "",
  "spoken_feedback": "",
  "debug_metadata": {}
}
```

## **Key Concepts**

```text
pipeline orchestration
module integration
offline inference
result schemas
error handling
debug metadata
```

## **Key Engineering Decisions**

```text
Build offline inference before API.
Keep business logic separate from API.
Return structured JSON.
Include debug metadata for future troubleshooting.
```

## **Deliverables**

```text
run_inference.py
analysis_pipeline.py
result_schema.py
inference_config.py
sample_output.json
```

## **Success Criteria**

Phase 12 is complete when:

```text
one video can produce a full analysis result
all modules connect cleanly
output JSON is stable
no manual intervention is needed
```

## **Future Impact**

Phase 13 API integration depends on this pipeline.

The API should only call this pipeline, not duplicate logic.

---

# **Phase 13 — API Integration**

## **🎯 Goal**

Expose the Smart Cricket analysis pipeline through a backend API.

This phase transforms:

```text
offline Python pipeline
```

into:

```text
backend-accessible ML service
```

## **Input → Output**

```text
Input:
uploaded video file

Output:
JSON response with prediction, score, and feedback
```

## **API Responsibilities**

```text
accept video upload
validate file
save temporary file
call inference pipeline
return structured result
handle errors
clean temporary files
```

## **Possible Endpoint**

```text
POST /analyze
```

## **Expected API Response**

```json
{
  "predicted_shot": "pull_shot",
  "shot_confidence": 0.87,
  "technique_match_score": 74,
  "coaching_tips": [
    "Improve your follow-through.",
    "Keep your head more stable."
  ]
}
```

## **Key Concepts**

```text
backend integration
request validation
file upload handling
structured API responses
temporary storage
error handling
frontend compatibility
```

## **Key Engineering Decisions**

```text
Do not mix API logic with ML logic.
API should call inference pipeline.
Keep response schema stable.
Add health check endpoint later.
```

## **Deliverables**

```text
api/app.py
api/routes.py
api/schemas.py
api/services.py
POST /analyze endpoint
health endpoint
API test script
```

## **Success Criteria**

Phase 13 is complete when:

```text
API accepts video upload
pipeline runs successfully
JSON response is returned
errors are handled cleanly
frontend can consume the response
```

## **Future Impact**

This phase prepares integration with your Smart Cricket web app.

---

# **Phase 14 — Voice Output**

## **🎯 Goal**

Convert coaching feedback into spoken audio.

This phase transforms:

```text
spoken_feedback text
```

into:

```text
voice coaching output
```

## **Input → Output**

```text
Input:
TTS-friendly feedback string

Output:
audio feedback
or audio-ready response
```

## **Voice System Philosophy**

Voice should make the system feel more like a real coach.

But it should come after:

```text
prediction
scoring
feedback
API
```

because voice depends on meaningful feedback.

## **Planned Flow**

```text
feedback engine
→ spoken_feedback string
→ TTS service
→ audio file / stream
→ frontend playback
```

## **Key Concepts**

```text
text-to-speech
audio generation
spoken feedback formatting
frontend playback
latency
voice UX
```

## **Key Engineering Decisions**

```text
Keep TTS as separate service.
Do not hardcode one provider too early.
Return text first, audio later.
Make spoken feedback concise.
```

## **Deliverables**

```text
tts_service.py
voice_config.py
audio_output/
spoken feedback integration
frontend audio-ready response
```

## **Success Criteria**

Phase 14 is complete when:

```text
feedback text can be converted to audio
audio can be returned or played
spoken feedback sounds natural
voice output matches visible feedback
```

## **Future Impact**

This phase completes the AI coach feeling.

Later, it can evolve into conversational coaching.

---

# **5. Long-Term Future Extensions**

After the core roadmap is complete, possible future upgrades include:

```text
real-time webcam inference
MediaPipe Holistic for hands
bat tracking
ball tracking
multi-camera analysis
personalized player profiles
progress tracking dashboard
mobile app integration
cloud deployment
real-time voice coach
session history
player improvement analytics
automatic mistake trend detection
```

---

# **6. Main Technical Risks**

## **Dataset Risks**

```text
small dataset
limited player diversity
camera variation
label noise
class imbalance
```

## **Pose Risks**

```text
landmark jitter
occlusion
fast motion blur
missing wrists/ankles
bad lighting
```

## **Feature Risks**

```text
feature redundancy
bad feature scaling
incorrect landmark assumptions
overfitting due to too many features
```

## **Model Risks**

```text
overfitting
poor generalization
shot class confusion
small validation set
```

## **Feedback Risks**

```text
overconfident feedback
wrong thresholds
generic coaching
misleading technique scores
```

## **Real-Time Risks**

```text
latency
buffering
multiple predictions
unstable segmentation
voice delay
```

---

# **7. Final Success Definition**

The project is successful when it can reliably perform:

```text
one cricket batting video
→ one final shot prediction
→ confidence score
→ technique match score
→ meaningful feedback
→ API response
→ future voice output
```

The strongest version of the project is:

```text
webcam/video
→ pose sequence
→ one completed shot detected
→ sequence classifier
→ biomechanical comparison
→ coach-like feedback
→ text + voice output
```

---

# **8. Final Roadmap Philosophy**

Smart Cricket should not be treated as:

```text
a model training project
```

It should be treated as:

```text
a complete AI engineering system
```

The model is only one part.

The real project includes:

```text
data design
pose extraction
preprocessing
feature engineering
temporal modeling
segmentation
scoring
feedback
inference
API
voice
```

That is what makes it an advanced ML portfolio project.