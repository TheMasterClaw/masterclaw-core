#!/bin/bash
# Groq Whisper Transcription
# Usage: ./groq-whisper.sh /path/to/audio.m4a

# Try to load from config file if env not set
if [ -z "$GROQ_API_KEY" ] && [ -f "$HOME/.openclaw/groq-key" ]; then
  GROQ_API_KEY=$(cat "$HOME/.openclaw/groq-key" | tr -d '\n')
fi

if [ -z "$GROQ_API_KEY" ]; then
  echo "Error: GROQ_API_KEY not set" >&2
  exit 1
fi

FILE="$1"
if [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
  echo "Usage: $0 <audio-file>" >&2
  exit 1
fi

MODEL="${2:-whisper-large-v3}"

curl -s https://api.groq.com/openai/v1/audio/transcriptions \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@$FILE" \
  -F "model=$MODEL" \
  -F "response_format=text"
