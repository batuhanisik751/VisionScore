#!/bin/bash
# Post-change hook: detects source file edits and triggers the post-change agent.
# Receives tool input as JSON on stdin.

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)

# Only trigger for source code files in src/visionscore/
if [[ "$FILE_PATH" =~ src/visionscore/.*\.py$ ]]; then
  cat <<'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "Source file changed. Run the post-change agent now: create/run tests, update README and .gitignore, and suggest a 3-6 word commit message. Follow .claude/agents/post-change.md exactly."
  }
}
EOF
fi

exit 0
