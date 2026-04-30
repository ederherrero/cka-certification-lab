# Guia de Cenários — CKA Exam Simulator

Este guia explica como usar o sistema de cenários para simular as tarefas práticas do exame CKA.

---

## O que são os cenários

Cada cenário replica o formato real do exame CKA:

- Você recebe um **enunciado** descrevendo o que está quebrado ou incompleto
- Trabalha no cluster para resolver o problema
- Ao terminar, executa um **verificador automático** que confirma se a solução está correta

Isso é diferente dos labs em `labs/` que são tutoriais para seguir. Aqui, o ambiente já está quebrado e você precisa diagnosticar e consertar — exatamente o que o exame cobra.

---

## Fluxo de uso

```
1. Listar cenários disponíveis
         ↓
2. Fazer deploy do cenário (ambiente quebrado)
         ↓
3. Ler o enunciado e resolver o problema
         ↓
4. Verificar se a solução está correta
         ↓
5. (Opcional) Resetar o cenário para tentar novamente
```

---

## Comandos

```bash
# Ver todos os cenários disponíveis com categoria e dificuldade
python cka-lab.py scenario list

# Implantar um cenário (quebra o ambiente e exibe o enunciado)
python cka-lab.py scenario deploy 01-node-notready

# Versão curta com só o número também funciona
python cka-lab.py scenario deploy 01

# Verificar se você resolveu corretamente
python cka-lab.py scenario verify 01

# Ver uma dica sem revelar a solução completa
python cka-lab.py scenario hint 01

# Desfazer o cenário e limpar o cluster
python cka-lab.py scenario reset 01
```

---

## Exemplo completo — do deploy ao verify

```bash
# 1. Listar os cenários
python cka-lab.py scenario list

# 2. Fazer deploy do cenário 12 (service sem endpoints)
python cka-lab.py scenario deploy 12
```

Saída esperada:
```
[info] [12-svc-no-endpoints] Service sem endpoints  (Networking, intermediario)

╔══════════════════════════════════════════════════════════════════╗
║  CENÁRIO 12 — Service sem endpoints                              ║
╠══════════════════════════════════════════════════════════════════╣
║  O Service 'web-svc' no namespace scenario-12 não está           ║
║  roteando tráfego. Os pods da aplicação estão Running mas        ║
║  o service não alcança nenhum deles.                             ║
║                                                                  ║
║  TAREFA                                                          ║
║  Corrija o Service 'web-svc' para que ele roteie tráfego para    ║
║  os pods do Deployment 'web' no namespace scenario-12.           ║
╚══════════════════════════════════════════════════════════════════╝

[ok]  Deployment 'web' criado com selector 'app=web' mas Service usa 'app=webapp' (errado).
[warn] Resolva o problema descrito acima.
[info] Quando terminar: python cka-lab.py scenario verify 12
```

```bash
# 3. Diagnosticar o problema
kubectl get endpoints web-svc -n scenario-12
kubectl describe service web-svc -n scenario-12
kubectl get pods -n scenario-12 --show-labels

# 4. Corrigir o seletor do service
kubectl edit service web-svc -n scenario-12
# Altere spec.selector.app de "webapp" para "web"

# 5. Verificar a solução
python cka-lab.py scenario verify 12
```

Saída esperada:
```
[ok]  CORRETO! Service 'web-svc' tem endpoints. O seletor está correto.
[info] Desfaça o cenário quando quiser: python cka-lab.py scenario reset 12
```

```bash
# 6. Limpar o cluster
python cka-lab.py scenario reset 12
```

---

## Se travar — usando as dicas

As dicas são progressivas: revelam onde olhar sem entregar a resposta.

```bash
python cka-lab.py scenario hint 12
```

```
[info] Dica — [12-svc-no-endpoints] Service sem endpoints

Dica 1: kubectl get endpoints web-svc -n scenario-12
        Se aparecer '<none>', o seletor do Service não bate com nenhum pod.

Dica 2: Compare o seletor do service com os labels dos pods:
        kubectl describe service web-svc -n scenario-12 | grep Selector
        kubectl get pods -n scenario-12 --show-labels
...
```

---

## Catálogo de cenários

### Troubleshooting — 30% do exame

| ID | Título | Dificuldade |
|---|---|---|
| `01-node-notready` | Node NotReady — kubelet parado em wk-2 | intermediário |
| `02-pod-crashloop` | Pod em CrashLoopBackOff — comando inválido | iniciante |
| `03-pod-oom` | Pod sendo OOMKilled — memory limit insuficiente | iniciante |
| `04-app-env-missing` | Variável de ambiente ausente no ConfigMap | intermediário |
| `05-scheduler-down` | kube-scheduler fora do ar | avançado |
| `06-deployment-stuck` | Deployment travado no rollout (maxSurge + maxUnavailable = 0) | avançado |

### Cluster Architecture — 25% do exame

| ID | Título | Dificuldade |
|---|---|---|
| `07-rbac-namespace` | ServiceAccount sem permissão de listar pods | intermediário |
| `08-rbac-clusterrole` | ClusterRole com acesso somente leitura global | intermediário |
| `09-etcd-backup` | Criar snapshot do etcd em /tmp/etcd-snapshot.db | intermediário |
| `10-kubelet-broken` | Kubelet com clusterDNS apontando para IP errado | avançado |
| `11-static-pod` | Criar static pod no control plane | intermediário |

### Services & Networking — 20% do exame

| ID | Título | Dificuldade |
|---|---|---|
| `12-svc-no-endpoints` | Service com seletor errado, sem endpoints | intermediário |
| `13-netpol-blocking` | NetworkPolicy bloqueando tráfego legítimo | avançado |
| `14-dns-broken` | CoreDNS com Corefile corrompido | avançado |
| `15-ingress-wrong` | Ingress apontando para service inexistente | avançado |

### Workloads & Scheduling — 15% do exame

| ID | Título | Dificuldade |
|---|---|---|
| `16-pod-pending-taint` | Pod Pending — taint no node sem toleration | intermediário |
| `17-pod-pending-resources` | Pod Pending — request de CPU maior que qualquer node | iniciante |
| `18-wrong-image` | Deployment com tag de imagem inexistente | iniciante |

### Storage — 10% do exame

| ID | Título | Dificuldade |
|---|---|---|
| `19-pvc-pending` | PVC com accessMode incompatível com o PV disponível | intermediário |
| `20-pod-volume-wrong` | Volume montado em path errado — dados não persistem | intermediário |

---

## Ordem de estudo sugerida

**Semana 1 — Conceitos básicos (iniciante)**

```bash
python cka-lab.py scenario deploy 02   # CrashLoopBackOff
python cka-lab.py scenario deploy 03   # OOMKilled
python cka-lab.py scenario deploy 17   # Pending por resources
python cka-lab.py scenario deploy 18   # Imagem errada
```

**Semana 2 — Intermediário (maior peso no exame)**

```bash
python cka-lab.py scenario deploy 01   # Node NotReady
python cka-lab.py scenario deploy 04   # Env var faltando
python cka-lab.py scenario deploy 07   # RBAC namespace
python cka-lab.py scenario deploy 08   # ClusterRole
python cka-lab.py scenario deploy 09   # Etcd backup
python cka-lab.py scenario deploy 12   # Service sem endpoints
python cka-lab.py scenario deploy 16   # Taint/Toleration
python cka-lab.py scenario deploy 19   # PVC Pending
python cka-lab.py scenario deploy 20   # Volume errado
```

**Semana 3 — Avançado**

```bash
python cka-lab.py scenario deploy 05   # Scheduler down
python cka-lab.py scenario deploy 06   # Rollout travado
python cka-lab.py scenario deploy 10   # Kubelet config
python cka-lab.py scenario deploy 13   # NetworkPolicy
python cka-lab.py scenario deploy 14   # DNS corrompido
python cka-lab.py scenario deploy 15   # Ingress errado
```

---

## Boas práticas durante os cenários

**Configure os aliases antes de começar** — economiza tempo como no exame real:

```bash
alias k=kubectl
export do='--dry-run=client -o yaml'
export now='--grace-period=0 --force'
```

**Fluxo de diagnóstico padrão:**

```bash
# 1. Ver o que está errado
kubectl get pods -n <namespace>
kubectl describe pod <nome> -n <namespace>

# 2. Ver os eventos (seção mais útil do describe)
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# 3. Ver logs
kubectl logs <pod> -n <namespace>
kubectl logs <pod> -n <namespace> --previous  # container que crashou

# 4. Verificar recursos relacionados
kubectl get all -n <namespace>
kubectl describe service <svc> -n <namespace>
```

**Não olhe a dica antes de tentar pelo menos 10 minutos.** O exame não tem dicas — construir o raciocínio de diagnóstico independente é o objetivo.

---

## Referência cruzada com os labs

Cada cenário corresponde a um lab de referência onde o conceito é explicado:

| Cenários | Lab de referência |
|---|---|
| 01, 02, 03, 04, 05, 06 | [labs/05-troubleshooting.md](labs/05-troubleshooting.md) |
| 07, 08, 09, 10, 11 | [labs/01-cluster-architecture.md](labs/01-cluster-architecture.md) |
| 12, 13, 14, 15 | [labs/03-services-networking.md](labs/03-services-networking.md) |
| 16, 17, 18 | [labs/02-workloads-scheduling.md](labs/02-workloads-scheduling.md) |
| 19, 20 | [labs/04-storage.md](labs/04-storage.md) |

Se travar em um cenário, leia a seção correspondente no lab antes de usar o `hint`.

---

## Currículo completo do exame

Para os temas, pesos e dicas gerais do exame: [cka-curriculum.md](cka-curriculum.md)
