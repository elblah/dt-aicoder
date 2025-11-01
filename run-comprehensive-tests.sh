#!/bin/bash

# Set test environment
export DISABLE_RETRY_PATTERNS=1
export YOLO_MODE=1

TESTS=(
    tests/comprehensive/streaming_adapter_comprehensive_test.py
    tests/comprehensive/animator_esc_functionality_test.py
    tests/comprehensive/animation_lifecycle_verification.py

    tests/comprehensive/tmux_animator_esc_test.py
    tests/comprehensive/tmux_esc_cancellation_test.py
)

count_not_ok=0
ret=0
for tst in ${TESTS[*]}; do
    echo -e "\nExecuting: $tst"
    if ! python $tst; then
        ret=1
        (( count_not_ok++ ))
    fi
done

tot_tests=${#TESTS[*]}
echo -e "\nTests ok? $(( tot_tests - count_not_ok )) of $tot_tests"

exit $ret
