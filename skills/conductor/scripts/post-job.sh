#!/bin/bash
# Post a job to Conductor Agent Network
# Usage: ./post-job.sh "Task description" "comma,separated,skills" priority retries

DESCRIPTION="$1"
SKILLS="$2"
PRIORITY="${3:-3}"
RETRIES="${4:-3}"

if [ -z "$DESCRIPTION" ]; then
  echo "Usage: $0 \"Task description\" \"skills\" [priority] [retries]"
  echo "Example: $0 \"Transcribe 10 min audio\" \"transcription,audio\" 3 3"
  exit 1
fi

echo "Opening Conductor Agent Network..."
agent-browser open https://conductor-rosy.vercel.app/

echo "Filling out job form..."
agent-browser fill 'textbox "Task Description"' "$DESCRIPTION"
agent-browser fill 'textbox "Required Skills (comma-separated)"' "$SKILLS"

# Note: Wallet connection required before submitting
# Click "Connect Wallet" first, then "Create Task"

echo "Job form filled. Connect wallet and click 'Create Task' to submit."
echo "Description: $DESCRIPTION"
echo "Skills: $SKILLS"
