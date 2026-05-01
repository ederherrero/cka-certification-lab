#!/usr/bin/env bash
set -euo pipefail

HOST_ONLY_BASE="${HOST_ONLY_BASE:-192.168.99}"
POD_CIDR="${POD_CIDR:-10.244.0.0/16}"
SERVICE_CIDR="${SERVICE_CIDR:-10.96.0.0/12}"
CALICO_VERSION="${CALICO_VERSION:-3.30.2}"
CLUSTER_NAME="${CLUSTER_NAME:-cka-lab}"

API_IP=$(hostname -I | tr ' ' '\n' | grep "^${HOST_ONLY_BASE}\." | head -1)
if [[ -z "$API_IP" ]]; then
  API_IP=$(hostname -I | awk '{print $1}')
fi

echo "[cp] API IP detectado: ${API_IP}"

echo "[cp] Inicializando cluster com kubeadm..."
kubeadm init \
  --apiserver-advertise-address="${API_IP}" \
  --pod-network-cidr="${POD_CIDR}" \
  --service-cidr="${SERVICE_CIDR}" \
  --node-name="${CLUSTER_NAME}-cp-1" \
  --ignore-preflight-errors=NumCPU

echo "[cp] Configurando kubeconfig..."
mkdir -p /home/vagrant/.kube
cp /etc/kubernetes/admin.conf /home/vagrant/.kube/config
chown vagrant:vagrant /home/vagrant/.kube/config

echo "[cp] Instalando Calico ${CALICO_VERSION}..."
export KUBECONFIG=/etc/kubernetes/admin.conf
kubectl apply -f "https://raw.githubusercontent.com/projectcalico/calico/v${CALICO_VERSION}/manifests/calico.yaml"

echo "[cp] Exportando kubeconfig para pasta compartilhada..."
mkdir -p /vagrant/shared
cp /etc/kubernetes/admin.conf /vagrant/shared/admin.conf
# Substituir IP interno pelo host-only para acesso externo
sed -i "s|https://.*:6443|https://${API_IP}:6443|g" /vagrant/shared/admin.conf
chmod 644 /vagrant/shared/admin.conf

echo "[cp] Gerando token de join para os workers..."
kubeadm token create --print-join-command > /vagrant/shared/join-command.sh
chmod 644 /vagrant/shared/join-command.sh

echo "[cp] Concluído. Cluster disponível em https://${API_IP}:6443"
