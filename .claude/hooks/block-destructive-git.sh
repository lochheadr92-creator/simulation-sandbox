#!/bin/bash
# PreToolUse hook: gate destructive git operations behind an explicit
# confirmation prompt, per CLAUDE.md hard rails:
#   "Destructive git: reset/checkout/clean/stash-drop on the working tree,
#    force-push, history rewrite, branch deletion."
# This does not silently block anything -- it forces an "ask" permission
# decision so the command surfaces a confirmation prompt even under
# auto-accept / permissive settings. The user can still approve it.
# Requires jq (see filter-run-output.sh for the same PATH fallback). If jq
# is missing, the hook no-ops and normal permission handling applies.

input=$(cat)

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

ask() {
  jq -n --arg reason "$1" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "ask",
      permissionDecisionReason: $reason
    }
  }'
}

# Only look at actual git invocations.
if ! echo "$cmd" | grep -qE '(^|[[:space:]&|;])git([[:space:]]|$)'; then
  echo "{}"
  exit 0
fi

# --- working-tree discard ---------------------------------------------------
if echo "$cmd" | grep -qE 'git[[:space:]]+reset([[:space:]]+--[a-z-]+)*[[:space:]]+--hard'; then
  ask "CLAUDE.md hard rail: 'reset --hard' discards uncommitted working-tree changes. Confirm this is intended before proceeding."
  exit 0
fi

if echo "$cmd" | grep -qE 'git[[:space:]]+checkout([[:space:]]+.*)?[[:space:]]--([[:space:]]|$)|git[[:space:]]+checkout[[:space:]]+\.([[:space:]]|$)'; then
  ask "CLAUDE.md hard rail: this 'git checkout' form discards working-tree changes rather than switching branches. Confirm this is intended before proceeding."
  exit 0
fi

if echo "$cmd" | grep -qE 'git[[:space:]]+restore([[:space:]]|$)' && ! echo "$cmd" | grep -qE -- '--staged'; then
  ask "CLAUDE.md hard rail: 'git restore' without --staged discards working-tree changes. Confirm this is intended before proceeding."
  exit 0
fi

if echo "$cmd" | grep -qE 'git[[:space:]]+clean([[:space:]]+-[a-zA-Z]*f[a-zA-Z]*|.*--force)'; then
  ask "CLAUDE.md hard rail: 'git clean -f' permanently deletes untracked files. Confirm this is intended before proceeding."
  exit 0
fi

if echo "$cmd" | grep -qE 'git[[:space:]]+stash[[:space:]]+(drop|clear)'; then
  ask "CLAUDE.md hard rail: 'git stash drop/clear' permanently discards stashed work. Confirm this is intended before proceeding."
  exit 0
fi

# --- force-push / branch deletion ------------------------------------------
if echo "$cmd" | grep -qE 'git[[:space:]]+push.*(--force([[:space:]]|$|-with-lease)|[[:space:]]-f([[:space:]]|$))'; then
  ask "CLAUDE.md hard rail: force-push can overwrite remote/upstream history. Confirm this is intended before proceeding."
  exit 0
fi

if echo "$cmd" | grep -qE 'git[[:space:]]+push[[:space:]]+[^[:space:]]+[[:space:]]+\+'; then
  ask "CLAUDE.md hard rail: a '+refspec' push forces the update, same as --force. Confirm this is intended before proceeding."
  exit 0
fi

if echo "$cmd" | grep -qE 'git[[:space:]]+branch.*[[:space:]]-D([[:space:]]|$)|git[[:space:]]+branch.*--delete.*--force|git[[:space:]]+push.*--delete'; then
  ask "CLAUDE.md hard rail: branch deletion. Confirm this is intended before proceeding."
  exit 0
fi

# --- history rewrite ---------------------------------------------------------
if echo "$cmd" | grep -qE 'git[[:space:]]+rebase|git[[:space:]]+filter-branch|git[[:space:]]+filter-repo|git[[:space:]]+commit.*--amend'; then
  ask "CLAUDE.md hard rail: history rewrite (rebase/filter-branch/filter-repo/amend). Confirm this is intended before proceeding."
  exit 0
fi

echo "{}"
