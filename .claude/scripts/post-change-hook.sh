#!/bin/bash
# Post-change hook: detects source file edits and triggers the post-change agent.
# Called by Claude Code after Edit/Write tool use.
# Receives tool input as JSON on stdin, and the file path via $TOOL_INPUT_FILE_PATH.

FILE_PATH="${TOOL_INPUT_FILE_PATH}"

# Only trigger for source code files in src/
if [[ "$FILE_PATH" == */src/visionscore/*.py ]]; then
  echo "Source file changed: $FILE_PATH"
  echo "Run the post-change agent now: create/run tests, update README and .gitignore, and suggest a 3-6 word commit message. Follow the instructions in .claude/agents/post-change.md exactly."
fi
