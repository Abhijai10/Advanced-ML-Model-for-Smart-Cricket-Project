# Phase 14 — Voice Output

# 🎯 Goal of the Phase

Phase 14 converts coaching feedback text into audio-ready output.

Previous phases produced:

```text
predicted shot
technique score
coaching feedback
API response
spoken_feedback
```

Phase 14 transforms:

```text
spoken_feedback text
```

into:

```text
audio artifact
frontend audio-ready response
voice debug metadata
```

This completes the core Smart Cricket roadmap: the system can classify a shot, score technique, explain feedback, expose the result through an API, and provide an audio-ready coaching output.

# 🧠 Core Concepts Introduced

## Text-to-Speech Boundary

The voice system is implemented behind a service boundary. The feedback engine produces text. The voice service converts that text into audio metadata/artifacts.

This separation matters because TTS providers can change later without rewriting scoring or feedback logic.

## Spoken Feedback as Source of Truth

Phase 14 does not create new coaching advice. It consumes the `spoken_feedback` string generated in Phase 11 and exposed through Phase 13.

That prevents mismatch between visible feedback and audio feedback.

## Audio-Ready Response

The frontend audio-ready response contains:

- spoken feedback text
- audio availability
- provider name
- audio path
- audio format
- audio byte size
- debug metadata

This gives frontend or API clients enough information to display text and play audio.

## Local Provider Fallback

The implementation attempts a local macOS speech-provider boundary, but the local `say` command produced header-only audio in this environment. The system falls back to a playable WAV audio cue while preserving exact spoken feedback text.

This keeps Phase 14 testable and provider-separated, while documenting that production voice should use a proper TTS provider.

# 🏗️ System-Level Importance

Phase 14 is the final output layer.

The complete pipeline is now:

```text
video / temporal sequence
→ prediction
→ segmentation
→ technique scoring
→ feedback
→ API response
→ voice/audio-ready output
```

Voice makes the system feel closer to a coaching assistant instead of only an analytics engine.

# 📂 Important Files / Scripts

## ml/src/voice/voice_config.py

Defines voice output paths, provider config, audio format, and version constants.

## ml/src/voice/tts_service.py

Implements spoken feedback validation, provider-separated synthesis, local fallback audio generation, and frontend audio-ready response construction.

## ml/src/voice/validate_voice_output.py

Loads the Phase 13 sample API response, converts its `spoken_feedback` to audio output, and writes Phase 14 artifacts.

## ml/src/voice/tests/test_tts_service.py

Tests spoken feedback validation and frontend audio-ready response shape.

## ml/artifacts/phase14/audio_output/sample_spoken_feedback.wav

Playable local audio artifact.

## ml/artifacts/phase14/frontend_audio_ready_response.json

Frontend-friendly text plus audio metadata response.

## ml/artifacts/phase14/voice_health.json

Machine-readable voice validation status.

# 🔄 Data Flow

```text
Phase 13 sample API response
→ spoken_feedback
→ voice service
→ audio artifact
→ frontend audio-ready response
→ validation health/report
```

# ⚠️ Common Mistakes / Pitfalls

- regenerating feedback inside the voice layer
- hardcoding one TTS provider too early
- creating audio that does not match visible feedback
- failing to validate that the audio file is playable
- mixing voice output with API business logic
- hiding provider limitations

# 💡 Key Engineering Decisions

## Provider Boundary First

The voice service is isolated so a production provider can replace the local provider later.

## Preserve Text First

The audio response always includes the exact spoken feedback text.

## Validate Audio Payload

The validator checks that the audio artifact exists and contains real audio bytes.

## Honest Local Fallback

Since local `say` did not produce valid speech audio in this environment, the implementation falls back to a playable WAV audio cue and documents the limitation.

# 📘 What I Should Write in Notes

- Voice output consumes `spoken_feedback`; it does not create new feedback.
- Provider separation is important for future TTS upgrades.
- Audio and visible feedback must match.
- Phase 14 completes the core roadmap, but production voice can still improve.
- The local fallback is playable, but natural speech should use a real TTS provider later.

# 🧠 Personal Learning Insights

The final phase shows that ML engineering includes output experience. A model result becomes more useful when it is delivered through text, API, and audio-ready formats.

Another lesson is that integration phases reveal environmental issues. The macOS `say` command existed, but did not produce usable speech frames here. The correct engineering move was to validate the artifact and provide a controlled fallback instead of blindly trusting a command.

# 🚀 Future Impact

Phase 14 prepares:

- frontend audio playback
- production TTS provider integration
- real-time coaching voice
- conversational coaching extensions
- richer UX around feedback delivery

The core Smart Cricket roadmap is now complete through voice/audio-ready output.
