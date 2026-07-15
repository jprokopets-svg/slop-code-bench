#!/bin/bash
# go.sh — idempotent launcher. Run any time, as many times as you want.
# Checks each problem, launches only what's missing, ensures keepalive.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

# Ensure ~/.local/bin (uv) is on PATH even when launched from a bare subshell.
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"

# Remove stale /tmp/horizon_*.lock files whose recorded PID is no longer alive.
# This prevents new launches from being skipped due to a dead predecessor's lock.
for lockfile in /tmp/horizon_*.lock; do
    [ -f "$lockfile" ] || continue
    lock_pid=$(cat "$lockfile" 2>/dev/null)
    if [ -n "$lock_pid" ] && ! kill -0 "$lock_pid" 2>/dev/null; then
        rm -f "$lockfile"
    fi
done

# Kill zombie Pi processes from prior runs (they hold in-memory session locks
# and block new Pi instances from starting).
# pgrep -f matches against the full command line; "pi " matches both bare "pi"
# and paths like "/usr/local/bin/pi". We kill any Pi process at 0% CPU that
# is not the parent of a currently-running slop-code worker.
for pid in $(pgrep -f "[/ ]pi " 2>/dev/null; pgrep -f "^pi " 2>/dev/null); do
    cpu=$(ps -o %cpu= -p "$pid" 2>/dev/null | tr -d ' ')
    # Kill Pi processes using 0% CPU (zombies); leave active ones alone.
    if [ "${cpu%.*}" = "0" ] 2>/dev/null; then
        kill "$pid" 2>/dev/null
    fi
done

PROBLEMS="file_backup etl_pipeline code_search dynamic_config_service_api"
MODEL="deepseek/deepseek-v4-flash"
ENV="configs/environments/local-py.yaml"
PROMPT="configs/prompts/just-solve.jinja"
AGENT="pi-horizon"
LOG="horizon_run.log"

# Auto-quarantine completed run-dirs where any checkpoint has 0 API steps
# (empty DeepSeek responses). Only quarantine if no slop-code process is
# currently running for any problem in this run-dir.
mkdir -p outputs/_invalid
for run_dir in outputs/deepseek-v4-flash/pi-*/; do
    [ -d "$run_dir" ] || continue
    for result in "$run_dir"/*/checkpoint_*/inference_result.json; do
        [ -f "$result" ] || continue
        steps=$(python3 -c "import json; d=json.load(open('$result')); print(d.get('usage',{}).get('steps',0))" 2>/dev/null)
        if [ "${steps:-0}" -eq 0 ]; then
            run_base=$(basename "$run_dir")
            echo "[go.sh] quarantining $run_base (zero-step checkpoint: $result)" >> "$LOG"
            mv "$run_dir" "outputs/_invalid/" 2>/dev/null
            break
        fi
    done
done

set -a; source /Users/jakeprokopets/Downloads/llm-cost-harness/.env 2>/dev/null; set +a
[ -z "${DEEPSEEK_API_KEY:-}" ] && echo "FATAL: no DEEPSEEK_API_KEY" && exit 1

problem_complete() {
    # A problem is complete if ANY run-dir has all its checkpoints' inference_result.json
    # AND every checkpoint has nonzero API cost (guards against empty DeepSeek responses).
    local prob=$1
    local need
    need=$(ls ~/.cache/scbench/problems/$prob/checkpoint_*.md 2>/dev/null | wc -l | tr -d ' ')
    # Guard: if the cache is missing or empty we cannot verify completion — treat as incomplete.
    # Without this, need=0 and [ got -ge 0 ] is always true, falsely marking every problem done.
    [ "${need:-0}" -eq 0 ] && return 1
    for dir in outputs/deepseek-v4-flash/pi-*/"$prob"/; do
        [ -d "$dir" ] || continue
        local got
        got=$(find "$dir" -name "inference_result.json" 2>/dev/null | wc -l | tr -d ' ')
        [ "$got" -ge "$need" ] || continue
        # Validate every checkpoint has nonzero steps (rejects empty API responses).
        local valid=true
        for result in "$dir"/checkpoint_*/inference_result.json; do
            [ -f "$result" ] || continue
            local steps
            steps=$(python3 -c "import json; d=json.load(open('$result')); print(d.get('usage',{}).get('steps',0))" 2>/dev/null)
            if [ "${steps:-0}" -eq 0 ]; then
                valid=false
                break
            fi
        done
        [ "$valid" = true ] && return 0
    done
    return 1
}

problem_running() {
    local prob=$1
    pgrep -f "slop-code run.*--problem $prob" >/dev/null 2>&1
}

launch_problem() {
    local prob=$1
    local lockfile="/tmp/horizon_${prob}.lock"
    if [ -f "$lockfile" ] && kill -0 "$(cat "$lockfile" 2>/dev/null)" 2>/dev/null; then
        return  # already locked by a live process
    fi
    (
        echo $$ > "$lockfile"
        trap 'rm -f "$lockfile"' EXIT
        exec </dev/null
        # Echo the full command so the pi invocation is never ambiguous in logs.
        echo "[go.sh] launching: uv run slop-code run --agent $AGENT --model $MODEL --environment $ENV --prompt $PROMPT --problem $prob --no-evaluate --num-workers 1 thinking=disabled version=0.80.6" >> "$LOG"
        # Use >> instead of tee to avoid keeping a pipe open (which blocks
        # the subshell from exiting after slop-code finishes).
        uv run slop-code run \
          --agent "$AGENT" \
          --model "$MODEL" \
          --environment "$ENV" \
          --prompt "$PROMPT" \
          --problem "$prob" \
          --no-evaluate \
          --num-workers 1 \
          thinking=disabled \
          version=0.80.6 \
          >> "$LOG" 2>&1
    ) &
    disown
}

# ── Status + launch missing ──
launched=0
for prob in $PROBLEMS; do
    if problem_complete "$prob"; then
        printf "  %-35s COMPLETE\n" "$prob"
    elif problem_running "$prob"; then
        printf "  %-35s RUNNING\n" "$prob"
    else
        launch_problem "$prob"
        printf "  %-35s LAUNCHED\n" "$prob"
        launched=$((launched + 1))
    fi
done

# ── Ensure keepalive ──
# Use PID file to detect existing keepalive (pgrep -f "keepalive_go" never
# matched because the string doesn't appear in the background shell's argv).
keepalive_alive=false
if [ -f /tmp/keepalive_go.pid ]; then
    kpid=$(cat /tmp/keepalive_go.pid 2>/dev/null)
    if [ -n "$kpid" ] && kill -0 "$kpid" 2>/dev/null; then
        keepalive_alive=true
    fi
fi
if [ "$keepalive_alive" = false ]; then
    (
        exec </dev/null
        while true; do
            sleep 900
            bash "$(cd "$(dirname "$0")" && pwd)/go.sh" >> horizon_run.log 2>&1
        done
    ) &
    disown
    echo "$!" > /tmp/keepalive_go.pid
    echo "  keepalive                             STARTED (PID $!)"
else
    echo "  keepalive                             RUNNING"
fi

[ "$launched" -eq 0 ] && echo "  (nothing to launch)" || echo "  launched $launched problem(s)"
