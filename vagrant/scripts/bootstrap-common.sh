#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

echo '[common] Updating apt cache...'
sudo apt-get update -y

echo '[common] Installing base packages...'
sudo apt-get install -y \
  apt-transport-https \
  ca-certificates \
  curl \
  gpg \
  jq \
  bash-completion \
  software-properties-common

echo '[common] Disabling swap...'
sudo swapoff -a || true
sudo sed -ri '/\sswap\s/s/^#?/#/' /etc/fstab || true

echo '[common] Loading kernel modules...'
cat <<MODULES | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
MODULES
sudo modprobe overlay || true
sudo modprobe br_netfilter || true

cat <<SYSCTL | sudo tee /etc/sysctl.d/99-kubernetes-cri.conf
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
SYSCTL
sudo sysctl --system

echo '[common] Installing containerd...'
sudo apt-get install -y containerd
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml >/dev/null
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
sudo systemctl restart containerd
sudo systemctl enable containerd

echo '[common] Installing Kubernetes packages...'
K8S_MAJOR_MINOR="${K8S_VERSION:-1.34}"
sudo mkdir -p /etc/apt/keyrings
curl -fsSL "https://pkgs.k8s.io/core:/stable:/v${K8S_MAJOR_MINOR}/deb/Release.key" | \
  sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v${K8S_MAJOR_MINOR}/deb/ /" | \
  sudo tee /etc/apt/sources.list.d/kubernetes.list

sudo apt-get update -y
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl

echo '[common] Done.'
