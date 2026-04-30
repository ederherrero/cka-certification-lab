# Arquitetura

## Objetivo

Fornecer um laboratório Kubernetes local, reproduzível e orientado a estudo de CKA.

## Componentes

- Host Windows
- VirtualBox
- Vagrant
- Ubuntu Server VMs
- kubeadm
- containerd
- CNI (Calico inicialmente)

## Topologia inicial

- 1 control plane
- 1 a 6 workers recomendados
- acesso remoto via LAN usando bridge

## Topologia futura

- 3 control planes
- workers dinâmicos
- HA via kubeadm
