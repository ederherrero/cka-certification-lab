#!/usr/bin/env bash
set -euo pipefail

MARKER=/var/lib/cka-lab/control-plane.done
sudo mkdir -p /var/lib/cka-lab

if [[ -f "$MARKER" ]]; then
  echo '[control-plane] Cluster already initialized. Skipping.'
  exit 0
fi

POD_CIDR="${POD_CIDR:-10.244.0.0/16}"
SERVICE_CIDR="${SERVICE_CIDR:-10.96.0.0/12}"
CNI="${CNI:-calico}"
HOST_ONLY_BASE="${HOST_ONLY_BASE:-192.168.99}"

# Usa o IP da interface host-only (estático, acessível pelo host).
# hostname -I retorna: 10.0.2.15 (NAT) | 192.168.99.10 (host-only) | 192.168.x.x (bridge)
API_IP=$(hostname -I | tr ' ' '\n' | grep "^${HOST_ONLY_BASE}\." | head -1)
if [[ -z "$API_IP" ]]; then
  echo "[control-plane] WARN: IP host-only não encontrado, usando primeiro IP disponível."
  API_IP=$(hostname -I | awk '{print $1}')
fi

echo "[control-plane] Initializing cluster on ${API_IP}..."
sudo kubeadm init \
  --apiserver-advertise-address "$API_IP" \
  --pod-network-cidr "$POD_CIDR" \
  --service-cidr "$SERVICE_CIDR"

mkdir -p /home/vagrant/.kube
sudo cp -f /etc/kubernetes/admin.conf /home/vagrant/.kube/config
sudo chown vagrant:vagrant /home/vagrant/.kube/config

JOIN_CMD=$(sudo kubeadm token create --print-join-command)
echo "$JOIN_CMD" | sudo tee /vagrant/.join-command >/dev/null

if [[ "$CNI" == "calico" ]]; then
  CALICO_VERSION="${CALICO_VERSION:-3.30.2}"
  kubectl --kubeconfig /etc/kubernetes/admin.conf apply -f \
    "https://raw.githubusercontent.com/projectcalico/calico/v${CALICO_VERSION}/manifests/calico.yaml"
fi

touch "$MARKER"
echo '[control-plane] Done.'
