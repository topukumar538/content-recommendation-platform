#!/bin/bash

# ── ContentPlatform Load Test Runner ─────────────────────────
# Stages: 10 → 100 → 500 → 1000 → 2000 → 3000 → 5000
# Stops automatically when success rate < 95% OR p95 > 2000ms
# Reports saved with success rate in filename

BASE_URL="http://localhost:8000"
STAGE_DURATION="60"        # seconds to run AFTER all users spawned
RESULTS_DIR="results"
STOP_SUCCESS_RATE=95       # stop if success rate drops below this
STOP_P95_MS=2000           # stop if p95 latency goes above this (ms)

mkdir -p $RESULTS_DIR

# stage format: "users:spawn_rate"
STAGES=(
  "10:5"
  "100:10"
  "500:25"
  "1000:50"
  "2000:100"
  "3000:100"
  "5000:100"
)

echo "============================================"
echo " ContentPlatform Load Test"
echo " Target: $BASE_URL"
echo " Stop conditions:"
echo "   Success rate < ${STOP_SUCCESS_RATE}%"
echo "   p95 latency  > ${STOP_P95_MS}ms"
echo "============================================"

for STAGE in "${STAGES[@]}"; do
  USERS=$(echo $STAGE | cut -d: -f1)
  SPAWN_RATE=$(echo $STAGE | cut -d: -f2)

  echo ""
  echo "► Stage: $USERS concurrent users (spawn rate: $SPAWN_RATE/sec)"

  # run locust headless, save csv stats
  locust \
    --headless \
    --users $USERS \
    --spawn-rate $SPAWN_RATE \
    --run-time ${STAGE_DURATION}s \
    --host $BASE_URL \
    --csv $RESULTS_DIR/raw_${USERS} \
    --html $RESULTS_DIR/raw_${USERS}.html \
    -f locustfile.py

  # ── parse results from CSV ────────────────────────────────
  STATS_FILE="$RESULTS_DIR/raw_${USERS}_stats.csv"

  if [ ! -f "$STATS_FILE" ]; then
    echo "  ✗ No stats file found, skipping analysis"
    continue
  fi

  # get aggregated row (last line = Aggregated)
  AGGREGATED=$(tail -1 $STATS_FILE)

  # extract values from CSV
  # CSV columns: Type,Name,Request Count,Failure Count,Median Response Time,Average Response Time,Min Response Time,Max Response Time,Average Content Size,Requests/s,Failures/s,50%,66%,75%,80%,90%,95%,98%,99%,99.9%,99.99%,100%
  TOTAL_REQUESTS=$(echo $AGGREGATED | cut -d',' -f3)
  TOTAL_FAILURES=$(echo $AGGREGATED | cut -d',' -f4)
  P95=$(echo $AGGREGATED | cut -d',' -f17)
  RPS=$(echo $AGGREGATED | cut -d',' -f10)

  # calculate success rate
  if [ "$TOTAL_REQUESTS" -gt 0 ]; then
    SUCCESS=$(echo "scale=2; (($TOTAL_REQUESTS - $TOTAL_FAILURES) / $TOTAL_REQUESTS) * 100" | bc)
  else
    SUCCESS="0"
  fi

  # round success rate for filename
  SUCCESS_INT=$(echo $SUCCESS | cut -d'.' -f1)
  P95_INT=$(echo $P95 | cut -d'.' -f1)

  # rename files with success rate
  mv "$RESULTS_DIR/raw_${USERS}.html" "$RESULTS_DIR/report_${USERS}_users_${SUCCESS_INT}percent.html"
  mv "$RESULTS_DIR/raw_${USERS}_stats.csv" "$RESULTS_DIR/stats_${USERS}_users_${SUCCESS_INT}percent.csv"

  # cleanup other csv files locust generates
  rm -f $RESULTS_DIR/raw_${USERS}_stats_history.csv
  rm -f $RESULTS_DIR/raw_${USERS}_failures.csv
  rm -f $RESULTS_DIR/raw_${USERS}_exceptions.csv

  echo "  ✓ Results:"
  echo "    Total requests : $TOTAL_REQUESTS"
  echo "    Failed         : $TOTAL_FAILURES"
  echo "    Success rate   : ${SUCCESS}%"
  echo "    p95 latency    : ${P95}ms"
  echo "    Requests/sec   : $RPS"
  echo "    Report         : $RESULTS_DIR/report_${USERS}_users_${SUCCESS_INT}percent.html"

  # ── check stop conditions ─────────────────────────────────
  SHOULD_STOP=0

  if [ "$SUCCESS_INT" -lt "$STOP_SUCCESS_RATE" ]; then
    echo ""
    echo "  ✗ STOP — success rate ${SUCCESS}% dropped below ${STOP_SUCCESS_RATE}%"
    SHOULD_STOP=1
  fi

  if [ "$P95_INT" -gt "$STOP_P95_MS" ]; then
    echo ""
    echo "  ✗ STOP — p95 latency ${P95}ms exceeded ${STOP_P95_MS}ms"
    SHOULD_STOP=1
  fi

  if [ "$SHOULD_STOP" -eq 1 ]; then
    echo ""
    echo "============================================"
    echo " Breaking point found at $USERS users"
    echo " Check results/ folder for all reports"
    echo "============================================"
    exit 0
  fi

  echo ""
  echo "  ✓ Passed both conditions — continuing to next stage"
  echo "  Sleeping 20s before next stage..."
  sleep 20

done

echo ""
echo "============================================"
echo " All stages passed both conditions"
echo " Your app handled all test stages"
echo " Check results/ folder for all reports"
echo "============================================"