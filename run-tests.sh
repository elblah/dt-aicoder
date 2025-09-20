#!/bin/bash

export AICODER_THEME="original" 
export YOLO_MODE=1 

python -m unittest -v
ret_unittest=$?

echo ""

./test_runner.py --full
ret_test_runner=$?

echo -e "\nResults:"

if [[ "$ret_unittest" == 0 && "$ret_test_runner" == 0 ]]; then
    echo "All tests ok"
else
    if [[ "$ret_unittest" != 0 ]]; then
        echo "Error: Unit tests NOT OK"
    fi

    if [[ "$ret_test_runner" != 0 ]]; then
        echo "Error: test_runner NOT OK"
    fi
    exit 1
fi
