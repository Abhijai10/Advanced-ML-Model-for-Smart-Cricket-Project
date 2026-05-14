# Phase 5.5 — Temporal Feature Engineering Redesign

# 🎯 Goal of This Redesign

The goal of this redesign is to correct a dataset/model contract mismatch discovered while starting the next model-building phase of the Smart Cricket Advanced ML project.

The earlier pipeline had successfully completed:

raw videos  
→ pose extraction  
→ pose cleaning  
→ normalization  
→ alignment  
→ fixed-length 60-frame pose sequences  
→ feature engineering  
→ dataset finalization  

However, the finalized dataset had the shape:
X_train.shape = (56, 32)

This means the dataset was rank-2:
[samples, features]

That representation is suitable for classical ML models or simple feed-forward models, but it is not suitable for GRU/BiLSTM temporal models.

The roadmap-aligned model direction expects temporal sequence models such as GRU and BiLSTM. These models require rank-3 tensors:

```text
[samples, time_steps, feature_dimension]
```

For Smart Cricket, the correct target representation should be:

```text
X_train_sequence.shape = (56, 60, 32)
```

Meaning:

```text
56 shot samples
60 frames per shot
32 biomechanical features per frame
```

So this redesign corrects the project from:

```text
sequence-derived tabular classification
```

to:

```text
true temporal cricket motion learning
```

---

# **🧠 What Architectural Mismatch Was Discovered?**

The discovered mismatch was between:

```text
the roadmap’s intended model architecture
```

and

```text
the actual dataset artifacts produced by the pipeline
```

The roadmap expects models that understand motion over time, especially GRU/BiLSTM-based temporal classifiers.

But the existing dataset artifacts were:

```text
X_train.npy → (56, 32)
X_val.npy   → (12, 32)
X_test.npy  → (12, 32)
```

This tells us that each cricket shot was represented as one summarized vector.

That means the model would receive:

```text
one shot = one row = 32 values
```

But a temporal model expects:

```text
one shot = sequence of frames = 60 rows of frame-wise features
```

So the model contract was broken.

The previous dataset answered:

```text
What were the overall statistics of this shot?
```

But the roadmap model needs:

```text
How did this shot evolve over time?
```

That difference is the heart of the redesign.

---

# **🧠 Why This Is Rooted in Phase 5 Representation Design**

This is not simply a Phase 6 mistake.

A more accurate diagnosis is:

```text
Phase 5 compressed the motion.
Phase 6 finalized the compressed output.
Phase 7 exposed the mismatch.
```

Phase 5 created a 32-feature representation using summary statistics such as:

```text
mean
min
max
total
change
score
```

Examples of summary-style features:

```text
lead_elbow_angle_mean
lead_elbow_angle_min
trunk_lean_max
motion_energy_total
weight_transfer_score
follow_through_extension
```

These are useful features, but they collapse an entire 60-frame sequence into one vector.

That means Phase 5 transformed:

```text
60-frame temporal motion
```

into:

```text
one summarized biomechanical fingerprint
```

This is not wrong for all ML models. It is perfectly reasonable for:

```text
Random Forest
SVM
Logistic Regression
MLP
```

But it is not compatible with roadmap-aligned temporal models such as:

```text
GRU
BiLSTM
sequence models
```

So the real correction is:

```text
Phase 5 must be extended/redesigned to produce per-frame features.
Phase 6 must then be rerun to finalize those per-frame features into temporal tensors.
```

---

# **🧠 Why Phase 6 Correctly Finalized the Wrong Representation**

Phase 6 itself did what it was asked to do.

It took the available feature dataset:

```text
features.csv
```

and converted it into:

```text
X.npy
y.npy
X_train.npy
X_val.npy
X_test.npy
y_train.npy
y_val.npy
y_test.npy
feature_schema.json
label_mapping.json
dataset_manifest.json
final_dataset_report.md
```

This was good dataset engineering.

The issue was not the finalization logic.

The issue was the input representation.

Phase 6 finalized:

```text
rank-2 tabular features
```

because Phase 5 produced:

```text
rank-2 tabular features
```

So the important lesson is:

```text
Dataset finalization cannot fix a representation mismatch upstream.
```

If the upstream features are tabular, Phase 6 will produce tabular ML artifacts.

If the upstream features are temporal, Phase 6 can produce temporal ML artifacts.

Therefore, the correction must start from representation design.

---

# **🔄 Sequence-Derived Tabular Features vs True Temporal Sequence Features**

## **Sequence-Derived Tabular Features**

The previous design was:

```text
full shot sequence
→ calculate summary statistics
→ one vector per shot
```

Example:

```text
one shot → [32 values]
```

Shape:

```text
[samples, features]
```

Example:

```text
(80, 32)
```

This preserves:

- overall movement tendencies
- statistical summaries
- rough biomechanical patterns
- interpretable shot-level information

But it loses:

- timing
- order
- frame-to-frame transitions
- motion rhythm
- acceleration phases
- follow-through evolution

This is useful for baseline tabular classification, but not enough for temporal intelligence.

---

## **True Temporal Sequence Features**

The redesigned approach is:

```text
full shot sequence
→ calculate features per frame
→ preserve 60-frame feature timeline
```

Example:

```text
one shot → 60 frames → 32 values per frame
```

Shape:

```text
[samples, time_steps, features]
```

Example:

```text
(80, 60, 32)
```

This preserves:

- temporal order
- motion progression
- swing rhythm
- backswing-to-downswing transition
- body rotation timing
- wrist acceleration timing
- follow-through development
- sequential biomechanics

This is the correct representation for GRU/BiLSTM.

---

# **🧠 Why Rank-2 Data Is Not Compatible With GRU/BiLSTM**

GRU and BiLSTM models are sequence models.

They expect data shaped like:

```text
[batch_size, sequence_length, feature_dimension]
```

For Smart Cricket:

```text
[batch_size, 60, 32]
```

This means the model processes a cricket shot like a timeline:

```text
frame 1  → 32 features
frame 2  → 32 features
frame 3  → 32 features
...
frame 60 → 32 features
```

The model learns dependencies such as:

```text
what happened earlier affects what happens later
```

But rank-2 data:

```text
[batch_size, 32]
```

has no time axis.

There is no concept of:

```text
before
after
transition
movement phase
```

So feeding rank-2 data to a temporal model is not just a shape error.

It is a conceptual mismatch.

The model architecture is asking:

```text
Where is the sequence?
```

But the dataset only provides:

```text
one summary vector
```

---

# **🏏 Why Cricket Shots Require Temporal Modeling**

A cricket shot is not a static posture.

A shot is a motion pattern.

For example, a cover drive contains:

```text
stance
→ trigger movement
→ front-foot movement
→ backswing
→ downswing
→ contact-like phase
→ follow-through
```

A pull shot contains a different motion evolution:

```text
weight transfer backward
→ body rotation
→ horizontal bat path
→ wrist/arm acceleration
→ follow-through across body
```

A defensive shot may be slower and more compact:

```text
stable head
→ controlled front-foot movement
→ limited swing
→ compact follow-through
```

These differences are temporal.

If we only summarize the entire motion into means and max values, we may know:

```text
wrist velocity was high
```

but not:

```text
when wrist velocity peaked
```

That timing matters.

A GRU/BiLSTM can learn patterns like:

```text
rotation before wrist acceleration
front-foot commitment before downswing
body center stabilizing during follow-through
```

That is why temporal modeling better matches the Smart Cricket vision.

---

# **🎯 New Target Tensor Shape**

The corrected target output is:

```text
X_sequence.shape = (80, 60, 32)
```

After splitting:

```text
X_train_sequence.shape = (56, 60, 32)
X_val_sequence.shape   = (12, 60, 32)
X_test_sequence.shape  = (12, 60, 32)
```

Labels remain one per sequence:

```text
y_train_sequence.shape = (56,)
y_val_sequence.shape   = (12,)
y_test_sequence.shape  = (12,)
```

This means:

```text
one complete shot sequence → one final shot label
```

Not:

```text
one frame → one label
```

This is very important.

The model should classify the complete batting action, not every frame independently.

---

# **🧩 Version 1 Temporal Feature Contract**

The redesigned representation will use:

```text
32 per-frame temporal features
```

organized into four balanced groups:

```text
8 joint angle features
8 posture/alignment features
8 motion dynamics features
8 cricket-specific temporal signals
```

This keeps the system:

- interpretable
- biomechanical
- consistent with previous Phase 5 thinking
- compatible with sequence models
- easier to validate

---

# **Category 1 — Joint Angle Features**

These describe body mechanics at each frame.

```text
1. lead_elbow_angle
2. trail_elbow_angle
3. lead_knee_angle
4. trail_knee_angle
5. lead_shoulder_angle
6. trail_shoulder_angle
7. shoulder_rotation_angle
8. hip_rotation_angle
```

Purpose:

```text
captures skeletal configuration and joint mechanics frame-by-frame
```

These features help the model understand how the batter’s arms, knees, shoulders, and hips are positioned during each phase of the shot.

---

# **Category 2 — Posture & Alignment Features**

These describe body balance and alignment per frame.

```text
9. trunk_lean
10. head_over_base_offset
11. head_to_lead_knee_alignment
12. shoulder_hip_separation
13. stance_width
14. body_center_offset_x
15. body_center_offset_y
16. upper_body_balance_offset
```

Purpose:

```text
captures stance, balance, head position, body lean, and body alignment
```

Important note:

Earlier names like:

```text
body_center_x
body_center_y
```

should be treated carefully.

The better temporal interpretation is:

```text
body_center_offset_x
body_center_offset_y
```

because absolute coordinates may become meaningless after normalization.

---

# **Category 3 — Motion Dynamics Features**

These describe movement between frames.

```text
17. lead_wrist_velocity
18. trail_wrist_velocity
19. lead_elbow_velocity
20. trail_elbow_velocity
21. body_center_velocity
22. shoulder_rotation_velocity
23. hip_rotation_velocity
24. frame_motion_energy
```

Purpose:

```text
captures speed, movement intensity, rotation timing, and swing energy
```

These features are especially important for temporal models because they describe how the player moves, not just where the player is.

---

# **Category 4 — Cricket-Specific Temporal Signals**

These are cricket-specific proxy signals per frame.

```text
25. front_foot_commitment_signal
26. back_foot_loading_signal
27. weight_transfer_signal
28. follow_through_height_signal
29. follow_through_extension_signal
30. lead_elbow_extension_signal
31. bat_side_wrist_height_signal
32. stance_to_swing_progress_signal
```

Purpose:

```text
captures cricket shot mechanics, swing phases, and movement progression
```

These are not raw pose landmarks.

They are engineered temporal signals designed to represent cricket-specific movement concepts.

That is acceptable because Smart Cricket is not just pose classification.

It is biomechanical motion analysis.

---

# **⚠️ Dead / Zero-Variance Feature Handling**

Earlier, some features became dead or near-zero after normalization/alignment.

Examples included:

```text
shoulder_rotation_angle_mean
body_center_shift_x
body_center_shift_y
body_center_velocity_mean
body_center_velocity_max
shoulder_rotation_velocity_mean
```

This does not mean the biomechanical ideas are useless.

It means the earlier representation caused those ideas to collapse.

The previous problem was:

```text
normalization + sequence-level summarization
```

removed useful variation.

The redesign should handle this differently.

Instead of keeping dead summary features, we should redesign them as temporal signals.

Example:

```text
old:
body_center_shift_x as one summary value

new:
body_center_offset_x across 60 frames
```

Example:

```text
old:
shoulder_rotation_velocity_mean

new:
shoulder_rotation_velocity per frame
```

This allows the temporal model to learn:

```text
how the signal changes over time
```

rather than only:

```text
one averaged value
```

---

# **🧪 Why Temporal Variance Validation Is Required**

The 32-feature contract is a Version 1 design.

It must be validated after implementation.

Once we build:

```text
X_sequence.shape = (80, 60, 32)
```

we must check:

```text
Does each feature vary across frames?
Does each feature vary across samples?
Does each feature vary across classes?
Are any features flat?
Are any features noisy?
Are any features duplicated?
```

This should produce something like:

```text
temporal_feature_variance_report.csv
```

The validation should detect:

- fully dead features
- near-zero variance features
- frame-wise flat features
- highly noisy features
- redundant features
- features that collapse after normalization

This is necessary because temporal models are sensitive to poor features.

A dead feature adds no learning signal.

A noisy feature may actively hurt learning.

So the feature design process should be:

```text
design temporal features
→ build tensors
→ validate variance
→ refine features
→ then train GRU/BiLSTM
```

---

# **🏗️ How This Prepares Phase 7 GRU/BiLSTM Model Building**

After this redesign, Phase 7 can correctly use:

```text
X_train_sequence.npy
```

with shape:

```text
(56, 60, 32)
```

Now the GRU/BiLSTM can process each shot as a sequence.

The model can learn:

- early stance patterns
- preparation movement
- swing acceleration
- rotational timing
- follow-through evolution
- class-specific motion trajectories

This makes Phase 7 roadmap-aligned.

The training flow becomes:

```text
temporal feature tensor
→ GRU/BiLSTM
→ one final shot prediction
```

This is much stronger than forcing a temporal model onto tabular data.

---

# **📡 How This Supports Future Webcam Streaming Inference**

The long-term Smart Cricket system is not just an offline classifier.

The future architecture should work like:

```text
webcam stream
→ continuous pose extraction
→ shot-start detection
→ capture motion window
→ build 60-frame temporal tensor
→ classify one completed shot
→ generate feedback
```

This redesign supports that.

Why?

Because inference will naturally produce frame-by-frame data.

A webcam stream gives:

```text
frame 1
frame 2
frame 3
...
```

So the training dataset should match that structure.

If training uses temporal tensors, then future inference can use the same format:

```text
[1, 60, 32]
```

That creates consistency between:

```text
training data
```

and:

```text
live inference data
```

This is critical.

If training uses only summary vectors but inference is streaming, the system must compress the stream before prediction.

That is possible, but less aligned with the long-term vision.

Temporal tensors are the better foundation for:

- shot segmentation
- one-shot prediction
- technique scoring
- mistake detection
- coaching feedback
- real-time analysis

---

# **🧠 Key Engineering Lessons**

## **1. Dataset/model contract must be checked early**

The most important lesson is:

```text
model architecture must match dataset tensor shape
```

A GRU/BiLSTM is not just a “better model.”

It requires the dataset to preserve time.

---

## **2. Feature engineering can accidentally destroy temporal information**

Even good features can be harmful if they compress away the information the model needs.

The previous Phase 5 features were interpretable, but they summarized the sequence.

That made them less suitable for temporal models.

---

## **3. Phase boundaries matter**

The corrected diagnosis is:

```text
Phase 5 representation issue
Phase 6 finalization consequence
Phase 7 discovery point
```

This is a mature way to understand pipeline failures.

---

## **4. The old dataset is still useful**

The old rank-2 dataset is not useless.

It can still be used for:

```text
classical ML baselines
Random Forest
SVM
Logistic Regression
MLP
```

But it should not be used as the roadmap-aligned GRU/BiLSTM dataset.

So both can coexist:

```text
ml/data/final/           → tabular baseline dataset
ml/data/final_temporal/  → temporal roadmap dataset
```

---

# **✅ Final Strategic Decision**

The project should now proceed with:

```text
Phase 5.5 — Temporal Feature Engineering Redesign
```

followed by:

```text
Phase 6 — Temporal Dataset Finalization
```

The corrected pipeline should become:

```text
raw videos
→ pose extraction
→ cleaning
→ normalization
→ alignment
→ fixed-length 60-frame pose sequences
→ per-frame biomechanical feature extraction
→ temporal feature tensor
→ temporal dataset finalization
→ GRU/BiLSTM model building
```

This is the correct roadmap-aligned direction.

The project is now shifting from:

```text
sequence-derived tabular classification
```

to:

```text
true temporal cricket motion intelligence
```

That shift is necessary for Smart Cricket’s long-term goal of becoming an AI-based cricket coaching system.