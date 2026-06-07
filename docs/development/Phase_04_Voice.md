# Phase 04: Voice

## Objective

Provide a fully local, consent-aware voice pipeline with bounded capture and clear failure behavior.

## Entry Criteria

- Phase 03 exit criteria approved.
- Microphone permission, capture indicator, and retention designs reviewed.
- Supported audio devices and hardware performance targets defined.

## Deliverables

- **OpenWakeWord:** on-device activation with configurable sensitivity and push-to-talk fallback.
- **Faster-Whisper:** local transcription with language configuration, voice activity detection, and partial/final results.
- **Piper:** local speech synthesis with user-selectable installed voices.
- Voice Agent adapter that turns transcripts into normal user requests and renders responses without bypassing Core.

## Pipeline

```mermaid
flowchart LR
    MIC[Microphone] --> WW[OpenWakeWord]
    WW --> VAD[Bounded Capture + VAD]
    VAD --> STT[Faster-Whisper]
    STT --> CORE[JARVIS Core]
    CORE --> TEXT[Text Response]
    TEXT --> TTS[Piper]
    TTS --> SPK[Speaker]
```

## Privacy and Safety Rules

- Wake-word processing is local and uses a short in-memory ring buffer.
- A visible and accessible indicator is active whenever audio is captured.
- Raw audio is deleted after transcription by default.
- Transcripts follow request-history retention, not audio retention.
- The user can disable wake word, microphone access, transcription storage, and speech output independently.
- Audio capture times out and cannot run silently in the background.
- TTS does not speak Restricted data unless explicitly requested in the current interaction.

## Work Breakdown

| ID | Task | Verification |
|---|---|---|
| VOC-001 | Device enumeration and permissions | Denied, missing, changed, and busy device states pass |
| VOC-002 | Wake word and push-to-talk | False accept/reject benchmark recorded |
| VOC-003 | Capture and VAD | Start/stop/timeout and indicator tests pass |
| VOC-004 | Transcription | Accuracy/latency benchmark across fixtures |
| VOC-005 | Voice request integration | Transcript follows standard policy/orchestration path |
| VOC-006 | Piper synthesis | Interruption, queue, device loss, and sensitive-output tests |
| VOC-007 | Accessibility controls | Keyboard, captions, reduced motion, and mute verified |

## Exit Criteria

- Voice journeys work with outbound network blocked.
- Audio does not persist by default and deletion is test verified.
- Capture state is always visible and announced accessibly.
- User interruption stops speech and cancellation reaches orchestration.
- Performance meets hardware-specific thresholds documented in the status file.
- False activation and transcription evaluations have accepted baselines.

