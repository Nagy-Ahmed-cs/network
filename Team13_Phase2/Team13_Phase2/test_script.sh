
#!/bin/bash

# ============================================================
# Phase-2 Test Runner (Linux / netem)
# ============================================================

INTERFACE="ens33"
ROOT_DIR="results"
PYTHON="python3"

SERVER_SCRIPT="server.py"
CLIENT_SCRIPT="client.py"

DURATION_DEFAULT=20
SERVER_SLEEP=1
SERVER_PORT=5555

mkdir -p "$ROOT_DIR"

# ------------------------------------------------------------
# Cleanup
# ------------------------------------------------------------
cleanup() {
    tc qdisc del dev $INTERFACE root 2>/dev/null
    pkill -f "$SERVER_SCRIPT"
    pkill -f "$CLIENT_SCRIPT"
    sleep 1
}

# ------------------------------------------------------------
# Start Server
# ------------------------------------------------------------
start_server() {
    $PYTHON $SERVER_SCRIPT > /dev/null 2>&1 &
    SERVER_PID=$!
    sleep $SERVER_SLEEP
}

# ------------------------------------------------------------
# Stop Server
# ------------------------------------------------------------
stop_server() {
    kill -INT $SERVER_PID 2>/dev/null
    sleep 2
    kill -9 $SERVER_PID 2>/dev/null
}

# ------------------------------------------------------------
# Apply netem
# ------------------------------------------------------------
apply_netem() {
    NETEM_CMD="$1"
    if [ "$NETEM_CMD" != "none" ]; then
        tc qdisc add dev $INTERFACE root netem $NETEM_CMD
        echo "[netem] applied: $NETEM_CMD"
        sleep 0.2
    fi
}

# ------------------------------------------------------------
# Run Clients (Wrapper Logic)
# ------------------------------------------------------------
run_clients() {
    DURATION=$1
    INTERVAL=$2
    LOSS_PROB=$3
    BATCH=$4

    START_TIME=$(date +%s)

    DEVICE_ID=$((RANDOM % 9000 + 1000))

    while true; do
        NOW=$(date +%s)
        ELAPSED=$((NOW - START_TIME))

        if [ $ELAPSED -ge $DURATION ]; then
            break
        fi

        RAND=$(awk -v seed=$RANDOM 'BEGIN{srand(seed); print rand()}')

        if (( $(echo "$RAND > $LOSS_PROB" | bc -l) )); then
            $PYTHON $CLIENT_SCRIPT \
                --id $DEVICE_ID \
                --interval $INTERVAL \
                --batch $BATCH \
                > /dev/null 2>&1
        else
            echo "[wrapper] simulated loss"
        fi

        sleep $INTERVAL
    done
}

# ------------------------------------------------------------
# Core Scenario Runner
# ------------------------------------------------------------
run_scenario() {
    NAME=$1
    DURATION=$2
    INTERVAL=$3
    LOSS_PROB=$4
    BATCH=$5
    NETEM=${6:-none}

    echo "============================================================"
    echo "[*] Scenario: $NAME"

    TEST_DIR="$ROOT_DIR/$NAME"
    rm -rf "$TEST_DIR"
    mkdir -p "$TEST_DIR"

    cleanup
    apply_netem "$NETEM"

    start_server

    run_clients "$DURATION" "$INTERVAL" "$LOSS_PROB" "$BATCH"

    stop_server
    cleanup

    # Collect outputs
    for f in telemetry_log.csv telemetry_reordered.csv metrics.json; do
        [ -f "$f" ] && cp "$f" "$TEST_DIR/"
    done

    echo "{\"duration\":$DURATION,\"interval\":$INTERVAL,\"loss\":$LOSS_PROB,\"batch\":$BATCH}" \
        > "$TEST_DIR/notes.json"

    echo "[*] Scenario '$NAME' finished"
    sleep 1
}

# ============================================================
# Run Scenarios (Same as Python Version)
# ============================================================

run_scenario "baseline_1s"        20 1   0.0  1
run_scenario "loss_5pct"          20 1   0.05 1
run_scenario "delay_100ms_10ms"   20 1   0.0  1 "delay 100ms 10ms"
run_scenario "interval_5s"        60 5   0.0  1
run_scenario "interval_30s"       120 30 0.0  1
run_scenario "batch_5"            30 1   0.0  5
run_scenario "batch_10"           30 1   0.0  10

cleanup
echo "[*] All scenarios finished."
