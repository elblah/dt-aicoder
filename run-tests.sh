#!/bin/bash

export AICODER_THEME="original"
export YOLO_MODE=1 

#python -m unittest discover --failfast -v
python -m pytest tests/ "$@"
ret_unittest=$?
printf "\n\n"

./app-run-tests.py --full
ret_test_runner=$?

echo -e "\nRunning ruff check for serious errors:"
ruff check aicoder --select E,F --ignore E501,F841,E712,F401,E722,F541
ret_ruff_check_serious=$?

echo -e "\nFinal Results:"

if [[ "$ret_unittest" == 0 && "$ret_test_runner" == 0 && "$ret_ruff_check_serious" == 0 ]]; then
    echo "All tests ok"
else
    if [[ "$ret_unittest" != 0 ]]; then
        echo "Error: Unit tests NOT OK"
    fi

    if [[ "$ret_test_runner" != 0 ]]; then
        echo "Error: test_runner NOT OK"
    fi

    if [[ "$ret_ruff_check_serious" != 0 ]]; then
        echo "Error: ruff check serious NOT OK"
    fi

    exit 1
fi
