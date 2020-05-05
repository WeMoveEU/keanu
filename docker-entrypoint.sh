#!/usr/bin/dumb-init /bin/bash

set -u
set -o pipefail # set $? to first non zero exit value
                # so we know when keanu failed when we pipe it to tee

trap 'exit 0' TERM # Okay exit on docker stop
trap '' USR1

if [ -n "${RESTART:-}" ]; then
    while true; do
        "$@" 2>&1 | tee /tmp/keanu.log

        if [ $? -gt 0 ]; then
            # Fail exit when our command fails
            exit 1
        fi
    done
else # just a normal one-off run
    exec "$@"
fi
