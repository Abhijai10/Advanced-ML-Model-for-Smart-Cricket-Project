# Phase 12 — Deep Interview Pack

# Question

What did Phase 12 add to the Smart Cricket system?

## Short Answer

It connected prediction, segmentation, scoring, and feedback into one offline inference pipeline that returns stable JSON.

## Deep Technical Explanation

Earlier phases produced separate modules. Phase 12 orchestrates them in order: validate temporal sequence, scale for model prediction, classify the shot, segment the motion, score technique, generate feedback, and serialize the result.

## Engineering Reasoning

An ML system needs an inference layer before API integration. Otherwise the API would duplicate business logic.

## Why This Decision Was Taken

The roadmap says to build offline inference before API and keep business logic separate from API transport.

## Tradeoffs / Risks / Limitations

Phase 12 v1 uses finalized temporal sequences, not raw uploaded video. Raw upload handling is deferred to Phase 13 and later integration work.

## Important Engineering Insight

A trained model is not a product. The inference pipeline is what turns model artifacts into usable analysis.

# Question

Why does Phase 12 use finalized temporal sequences instead of raw video upload?

## Short Answer

Because Phase 12 is the offline ML orchestration layer; API upload handling belongs to Phase 13.

## Deep Technical Explanation

The current locked temporal contract is `[60,32]`. Phase 12 validates and analyzes that contract end to end. Raw video upload introduces transport, temporary storage, and service concerns, which are API responsibilities.

## Engineering Reasoning

Separating inference from API keeps the system testable and avoids mixing ML logic with backend routing.

## Why This Decision Was Taken

The roadmap explicitly says to build offline inference before API integration.

## Tradeoffs / Risks / Limitations

The pipeline is not yet a complete raw-video user application. It is the core analysis engine that later phases will wrap.

## Important Engineering Insight

Good systems expose ML logic as a clean callable module before making it a web service.

# Question

How does the pipeline handle scaling?

## Short Answer

It uses the train-only scaler for model prediction, but keeps raw temporal features for segmentation and scoring.

## Deep Technical Explanation

The recurrent classifier was trained on scaled features. Therefore inference must apply the saved Phase 8 scaler before calling the model. But segmentation and scoring depend on raw feature magnitudes and template ranges, so they use the original sequence.

## Engineering Reasoning

Using scaled features for scoring would break the Phase 10 templates. Using raw features for the model would break the training/inference contract.

## Why This Decision Was Taken

Each module must receive the representation it was designed and validated for.

## Tradeoffs / Risks / Limitations

The pipeline must carefully maintain both raw and scaled versions of the sequence.

## Important Engineering Insight

Inference bugs often come from representation mismatch, not model architecture.

# Question

What is included in the Phase 12 output JSON?

## Short Answer

It includes prediction, confidence, technique score, issues, tips, detailed feedback, spoken feedback, debug metadata, segmentation, and source metadata.

## Deep Technical Explanation

The top-level keys match the roadmap's expected output. Additional nested structures preserve class probabilities, segmentation metadata, and source traceability.

## Engineering Reasoning

The API should return stable fields, but engineers also need enough metadata to debug pipeline behavior.

## Why This Decision Was Taken

Phase 13 depends on a stable response schema.

## Tradeoffs / Risks / Limitations

The JSON is larger than a minimal response, but the extra metadata is useful for debugging.

## Important Engineering Insight

Stable output schemas are contracts between ML, backend, and frontend.

# Question

How does Phase 12 reuse earlier phases?

## Short Answer

It loads the Phase 8 checkpoint, calls the Phase 9 segmenter, calls the Phase 10 scorer, and calls the Phase 11 feedback engine.

## Deep Technical Explanation

Phase 12 does not duplicate business logic. It imports and orchestrates already-validated modules.

## Engineering Reasoning

Duplication would create inconsistent predictions, scores, or feedback between offline and API paths.

## Why This Decision Was Taken

The roadmap says the API should call the inference pipeline, not duplicate logic.

## Tradeoffs / Risks / Limitations

Changes in upstream modules can affect inference output, so validation must be rerun when those modules change.

## Important Engineering Insight

Orchestration should compose modules, not rewrite them.

# Question

Why is debug metadata important?

## Short Answer

It explains which artifacts and module versions produced the output.

## Deep Technical Explanation

The output records pipeline version, model artifact, template artifact, segmentation completion, feedback source, and input contract.

## Engineering Reasoning

When an API result looks wrong, debug metadata helps identify whether the issue came from model prediction, scoring, feedback, or input mismatch.

## Why This Decision Was Taken

The roadmap calls out error handling and debug metadata as key Phase 12 concepts.

## Tradeoffs / Risks / Limitations

Debug metadata increases response size, but it improves maintainability.

## Important Engineering Insight

ML inference needs observability just like backend services.

# Question

How does Phase 12 prepare Phase 13?

## Short Answer

It gives Phase 13 a clean pipeline function and stable JSON response to expose through an API.

## Deep Technical Explanation

Phase 13 should validate uploads, call the Phase 12 pipeline, return its JSON, and handle errors. It should not implement model loading, scoring, or feedback generation itself.

## Engineering Reasoning

This separation keeps API code thin and reduces the chance of inconsistent behavior.

## Why This Decision Was Taken

The roadmap says API integration depends on the inference pipeline.

## Tradeoffs / Risks / Limitations

The API still needs file validation, temporary storage, and raw-video preprocessing integration.

## Important Engineering Insight

The cleanest APIs are wrappers around stable application services.
