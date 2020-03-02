#!/usr/bin/dumb-init /bin/bash

set -u
set -o pipefail # set $? to first non zero exit value
                # so we know when keanu failed when we pipe it to tee

trap 'exit 0' TERM

if [ "$1" = "-r" ]; then
    RESTART=1;
    shift
else
    RESTART=0
fi

FAIL_WAIT=0

if [ $RESTART -eq 1 ]; then
    while true; do
        "$@" 2>&1 | tee /tmp/keanu.log
        if [ $? -gt 0 ]; then
            # error
            aborted_error=$(grep -B 1 Aborted /tmp/keanu.log)
            traceback_error=$(grep -A 1000 '^Traceback' /tmp/keanu.log)
            if [ -n "$aborted_error" -o -n "$traceback_error" ]; then
                echo "REPORTING ERROR TO ENDPOINT?"
                if [ -n "$aborted_error" ]; then 
                    echo "$aborted_error"
                fi
                if [ -n "$traceback_error" ]; then
                    echo "$traceback_error"
                fi
            fi
            FAIL_WAIT=$(printf "%d" $(( ($FAIL_WAIT + 5) * 110 / 100 )))
            echo $(printf "Sleeping for %ds" $FAIL_WAIT)
            sleep $FAIL_WAIT
        else
            FAIL_WAIT=0
        fi
    done
else
    exec "$@"
fi
