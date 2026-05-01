#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="${CLUSTER_NAME:-cka-lab}"
NODE_INDEX="${NODE_INDEX:-1}"
NODE_NAME="${CLUSTER_NAME}-wk-${NODE_INDEX}"

echo "[worker] Aguardando join-command do control plane..."
for i in $(seq 1 60); do
  if [[ -f /vagrant/shared/join-command.sh ]]; then
    echo "[worker] join-command encontrado."
    break
  fi
  echo "[worker] Aguardando... (${i}/60)"
  sleep 10
done

if [[ ! -f /vagrant/shared/join-command.sh ]]; then
  echo "[worker] ERRO: join-command não encontrado após 10 minutos."
  exit 1
fi

echo "[worker] Entrando no cluster como ${NODE_NAME}..."
bash /vagrant/shared/join-command.sh --node-name "${NODE_NAME}"

echo "[worker] ${NODE_NAME} adicionado ao cluster."
