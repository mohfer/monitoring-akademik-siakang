#!/bin/sh
set -e

# Self-heal ownership of bind-mounted data dirs. The Docker daemon may create
# missing bind-mount sources as root on fresh deployments, which a non-root
# process cannot write to. Fix it here, then drop to the unprivileged app user.
if [ "$(id -u)" = "0" ]; then
    mkdir -p /app/data/logs /app/data/db /app/data/value
    chown -R app:app /app/data
    exec gosu app "$@"
fi

exec "$@"
