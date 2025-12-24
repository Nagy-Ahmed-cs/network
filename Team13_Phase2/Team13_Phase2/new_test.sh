#!/bin/bash

# Configuration
INTERFACE="lo"          # Loopback interface for local testing
SERVER_IP="127.0.0.1"
DURATION=65             # 60s test + 5s buffer as per PDF
PYTHON="python3"

# Colors for output
GREEN='\033[0;32m'
NC='\033[0m' 

function cleanup() {
    echo "Cleaning up..."
    sudo tc qdisc del dev $INTERFACE root 2>/dev/null
    pkill -f server.py
}

function run_test() {
    local scenario_name=$1
    local netem_cmd=$2
    local interval=$3
    local batch=$4

    echo -e "${GREEN}>>> Starting Scenario: $scenario_name (Interval: ${interval}s, Batch: ${batch})${NC}"
    
    # 1. Apply Network Impairment
    sudo tc qdisc del dev $INTERFACE root 2>/dev/null
    if [ "$netem_cmd" != "none" ]; then
        sudo tc qdisc add dev $INTERFACE root $netem_cmd
        echo "Applied: $netem_cmd"
    fi

    # 2. Start Server in background
    $PYTHON server.py &
    SERVER_PID=$!
    sleep 2

    # 3. Start Client
    $PYTHON client.py --id 101 --interval $interval --batch $batch
    
    # 4. Cleanup for next run
    kill $SERVER_PID
    wait $SERVER_PID 2>/dev/null
    
    # 5. Move results to a scenario-specific folder
    mkdir -p "results/$scenario_name"
    mv telemetry_log.csv "results/$scenario_name/log.csv"
    mv telemetry_reordered.csv "results/$scenario_name/reordered.csv"
    mv metrics.json "results/$scenario_name/metrics.json"
    
    echo "Results saved to results/$scenario_name/"
    echo "--------------------------------------------"
}

# Ensure script is run as root for tc commands
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run with sudo to apply network impairments." 
   exit 1
fi

# Create results directory
mkdir -p results
trap cleanup EXIT

# --- SCENARIO 1: Baseline (Acceptance Criteria: >=99% received) ---
run_test "Baseline" "none" 1 1

# --- SCENARIO 2: Loss 5% (Acceptance Criteria: Detect gaps/duplicates) ---
# Command from Page 10 of PDF
run_test "Loss_5pct" "netem loss 5%" 1 1

# --- SCENARIO 3: Delay & Jitter (Acceptance Criteria: Correct reordering) ---
# Command from Page 10 of PDF: 100ms delay with 10ms jitter
run_test "Delay_Jitter" "netem delay 100ms 10ms" 1 1

# --- SCENARIO 4: Configurable Intervals (30s interval test) ---
# Required by Section 2: "test all: 1s, 5s, 30s"
run_test "Interval_30s" "none" 30 1

echo -e "${GREEN}All experiments completed successfully.${NC}"
