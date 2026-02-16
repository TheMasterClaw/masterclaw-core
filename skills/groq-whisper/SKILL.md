---
name: groq-whisper
description: Transcribe audio using Groq's Whisper API (fast, cheap voice transcription).
---

# Groq Whisper

Transcribe audio files using Groq's Whisper API.

## Setup

Set your Groq API key:
```bash
export GROQ_API_KEY="gsk_..."
```

## Usage

```bash
./skills/groq-whisper/groq-whisper.sh /path/to/audio.m4a
```

## Models

- `whisper-large-v3` (default)

## Notes

- Groq Whisper is fast and cheap (~$0.04/hour of audio)
- Supports: m4a, mp3, mp4, mpeg, mpga, ogg, wav, webm
