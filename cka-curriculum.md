# CKA — Currículo Oficial do Exame

**Última verificação:** 30/04/2026  
**Fonte:** [Linux Foundation](https://training.linuxfoundation.org/certification/certified-kubernetes-administrator-cka/) · [CNCF](https://www.cncf.io/training/certification/cka/) · [Repositório oficial do currículo](https://github.com/cncf/curriculum)  
**Versão do Kubernetes no exame:** 1.32 / 1.33 (atualizado dentro de 4–8 semanas após cada release)

---

## Formato do exame

| Item | Detalhe |
|---|---|
| Duração | 2 horas |
| Formato | Online, proctored, 100% prático (linha de comando) |
| Questões | ~17 tarefas práticas |
| Nota mínima | 66% |
| Validade | 2 anos |
| Documentação permitida | kubernetes.io, kustomize.io (durante o exame) |

---

## Domínios e pesos

| # | Domínio | Peso |
|---|---|---|
| 1 | Troubleshooting | 30% |
| 2 | Cluster Architecture, Installation & Configuration | 25% |
| 3 | Services & Networking | 20% |
| 4 | Workloads & Scheduling | 15% |
| 5 | Storage | 10% |

---

## 1. Troubleshooting — 30%

O domínio com maior peso. Espere questões de diagnóstico onde algo já está quebrado e você precisa identificar e corrigir.

- Avaliar uso de recursos de cluster e nodes (CPU, memória)
- Diagnosticar falhas em componentes do cluster (API server, scheduler, etcd, kubelet)
- Diagnosticar falhas em nodes (node NotReady, kubelet parado)
- Monitorar e analisar logs de containers
- Diagnosticar falhas em aplicações (pod CrashLoopBackOff, ImagePullBackOff, OOMKilled)
- Troubleshooting de networking (serviços sem endpoint, DNS não resolve)
- Troubleshooting de volumes (pod preso em pending por PVC)

---

## 2. Cluster Architecture, Installation & Configuration — 25%

- Arquitetura do Kubernetes (control plane, worker nodes, componentes)
- Instalar e configurar cluster com kubeadm
- Realizar upgrade de cluster com kubeadm (control plane → workers)
- Configurar RBAC (Roles, ClusterRoles, RoleBindings, ClusterRoleBindings)
- Gerenciar ServiceAccounts
- Backup e restore do etcd
- Configurar cluster altamente disponível (HA)
- Entender CRI (Container Runtime Interface) — containerd, CRI-O
- Entender CNI (Container Network Interface) — plugins de rede
- Helm — instalar, atualizar e remover aplicações com charts
- Kustomize — gerenciar variações de manifests de forma declarativa

---

## 3. Services & Networking — 20%

- Configurar conectividade de rede entre Pods
- Services: ClusterIP, NodePort, LoadBalancer, ExternalName
- Endpoints e EndpointSlices
- Ingress Controllers e Ingress Resources
- **Gateway API** (novo em 2025) — HTTPRoute, Gateway, GatewayClass
- Network Policies — restringir tráfego entre pods/namespaces
- CoreDNS — resolução de nomes dentro do cluster
- Service discovery

---

## 4. Workloads & Scheduling — 15%

- Deployments — criar, atualizar, rollback, escalar
- StatefulSets — workloads com estado e identidade estável
- DaemonSets — garantir um pod por node
- Jobs e CronJobs
- Resource Requests e Limits (CPU e memória)
- LimitRange e ResourceQuota por namespace
- Horizontal Pod Autoscaler (HPA)
- Node Selectors, Node Affinity, Pod Affinity e Anti-Affinity
- Taints e Tolerations
- ConfigMaps e Secrets — injeção em pods (env vars e volumes)
- Labels, Selectors e Annotations

---

## 5. Storage — 10%

- PersistentVolumes (PV) — criação e configuração
- PersistentVolumeClaims (PVC) — solicitação de volumes
- StorageClasses — provisioning dinâmico
- Access Modes — ReadWriteOnce, ReadOnlyMany, ReadWriteMany
- Reclaim Policies — Retain, Delete, Recycle
- Volumes efêmeros — emptyDir, configMap, secret, hostPath
- CSI (Container Storage Interface)

---

## Mudanças do currículo em 2025 (vigentes desde 18/02/2025)

### Adicionado
- **Helm** — gerenciamento de aplicações com charts
- **Kustomize** — customização declarativa de manifests
- **Gateway API** — substituto moderno ao Ingress
- **CNI, CSI, CRI** — compreensão dos plugins de extensão do Kubernetes

### Removido
- Provisionamento de infraestrutura subjacente para clusters (passou para plataformas gerenciadas)

---

## Dicas gerais para o exame

- Configure os aliases antes de começar:
  ```bash
  alias k=kubectl
  export do='--dry-run=client -o yaml'
  export now='--grace-period=0 --force'
  ```
- Use `kubectl explain <recurso>.<campo>` para consultar a API sem sair do terminal
- Use `kubectl -n <namespace> get all` para ter uma visão rápida de um namespace
- Memorize os comandos de backup do etcd — caem com frequência
- Saiba fazer upgrade de cluster passo a passo (control plane primeiro, depois workers)
- Pratique muito `kubectl logs`, `kubectl describe` e `kubectl exec` para troubleshooting
