#!/usr/bin/env bash
set -euo pipefail

MARKER=/var/lib/cka-lab/worker.done
sudo mkdir -p /var/lib/cka-lab

if [[ -f "$MARKER" ]]; then
  echo '[worker] Node already joined. Skipping.'
  exit 0
fi

for _ in $(seq 1 60); do
  if [[ -f /vagrant/.join-command ]]; then
    break
  fi
  echo '[worker] Waiting for join command...'
  sleep 10
done

if [[ ! -f /vagrant/.join-command ]]; then
  echo '[worker] join command not found after waiting.' >&2
  exit 1
fi

JOIN_CMD=$(cat /vagrant/.join-command)
sudo $JOIN_CMD

touch "$MARKER"
echo '[worker] Done.'
