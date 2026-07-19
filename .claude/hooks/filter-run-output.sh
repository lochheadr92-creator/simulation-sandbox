#!/bin/bash
# PreToolUse hook: keep verbose run output out of the context window.
# - pytest runs  -> keep failures, errors, and the final summary line (pass counts survive,
#                   so the "N executed passed; M excluded" reporting rule still has its evidence)
# - harness runs -> if output is NOT already redirected to a file, pipe through a grep that
#                   keeps only the summary keys the reporting rules require
# Everything else passes through untouched. Requires jq (ships with git-bash on Windows via
# `pacman`/scoop, or install from https://jqlang.org). If jq is missing, the hook no-ops.

input=$(cat)

# Windows: winget-installed jq may not be on PATH in fresh shells.
if ! command -v jq >/dev/null 2>&1; then
  export PATH="$PATH:/c/Users/RJLoc/AppData/Local/Microsoft/WinGet/Links:/c/Users/RJLoc/AppData/Local/Microsoft/WinGet/Packages/jqlang.jq_Microsoft.Winget.Source_8wekyb3d8bbwe"
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "{}"
  exit 0
fi

cmd=$(echo "$input" | jq -r '.tool_input.command // empty')

if [ -z "$cmd" ]; then
  echo "{}"
  exit 0
fi

# Skip rewriting when the agent already handled its own output (redirect to a
# file, or an existing pipe/filter). Double-filtering is harmless but noisy.
already_handled() {
  echo "$cmd" | grep -qE '(>[[:space:]]*[^&]|\|)'
}

emit() {
  # Safely JSON-encode the rewritten command with jq (naive echo breaks on quotes).
  jq -n --arg c "$1" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "allow",
      updatedInput: { command: $c }
    }
  }'
}

# --- pytest ---------------------------------------------------------------
# Match python -m pytest / pytest invocations. Keep FAILED/ERROR blocks with a
# little context plus the ===== summary lines (which carry "N passed").
if echo "$cmd" | grep -qE '(^|[[:space:]])(python[0-9.]* -m pytest|pytest)([[:space:]]|$)'; then
  # Don't rewrite if the agent already redirected output to a file.
  if ! already_handled; then
    emit "$cmd 2>&1 | grep -E -B 1 -A 5 '(FAILED|ERRORS?|error:|=====|passed|failed|warnings summary)' | tail -120"
    exit 0
  fi
fi

# --- scenario harness -----------------------------------------------------
# living_agent_harness.py runs print plenty. The protocol says redirect to a
# file and read back the summary block; this is the safety net if the agent
# forgets. Keeps exactly the fields the reporting rules require.
if echo "$cmd" | grep -q 'living_agent_harness'; then
  if ! already_handled; then
    emit "$cmd 2>&1 | grep -E '(repeat_matches|replay_matches|final_state_hash|group_norm_summary|accepted|deaths|death_count|ticks|scenario|seed|Traceback|Error)' | tail -80"
    exit 0
  fi
fi

echo "{}"
