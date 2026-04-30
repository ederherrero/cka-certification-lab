# Cenários de Simulação — CKA Exam

Cada cenário simula uma tarefa real do exame. Execute com:

```bash
python cka-lab.py scenario list              # listar todos os cenários
python cka-lab.py scenario deploy <id>       # implantar o estado quebrado/incompleto
python cka-lab.py scenario verify <id>       # verificar se a solução está correta
python cka-lab.py scenario reset <id>        # desfazer o cenário (limpar)
python cka-lab.py scenario hint <id>         # ver dica sem ver a solução completa
```

---

## Troubleshooting — 30% do exame (6 cenários)

> Referência: [`labs/05-troubleshooting.md`](05-troubleshooting.md)

| ID | Título | O que está quebrado | O que você precisa entregar |
|---|---|---|---|
| `01-node-notready` | Node NotReady | kubelet parado em `wk-2` | node voltando ao status Ready |
| `02-pod-crashloop` | Pod em CrashLoopBackOff | comando inválido no container | pod Running estável |
| `03-pod-oom` | Pod sendo OOMKilled | memory limit muito baixo para a aplicação | pod Running sem reiniciar |
| `04-app-env-missing` | Aplicação não inicia | variável de ambiente ausente no ConfigMap referenciado pelo pod | pod Running e variável presente |
| `05-scheduler-down` | Pods travados em Pending | kube-scheduler fora do ar (manifest removido) | scheduler Running, pods agendados |
| `06-deployment-stuck` | Deployment travado no rollout | `maxSurge: 0` e `maxUnavailable: 0` simultaneamente | rollout concluído com sucesso |

---

## Cluster Architecture, Installation & Configuration — 25% do exame (5 cenários)

> Referência: [`labs/01-cluster-architecture.md`](01-cluster-architecture.md)

| ID | Título | O que está quebrado / incompleto | O que você precisa entregar |
|---|---|---|---|
| `07-rbac-namespace` | RBAC faltando | ServiceAccount `app-sa` no namespace `dev` sem permissão de listar pods | `can-i list pods` retornando `yes` |
| `08-rbac-clusterrole` | ClusterRole faltando | usuário `monitor` precisa de leitura em nodes e pods em todos os namespaces | ClusterRoleBinding criado e verificado |
| `09-etcd-backup` | Backup do etcd | nenhum backup existe | snapshot em `/tmp/etcd-snapshot.db` com status válido |
| `10-kubelet-broken` | Kubelet com config errada | kubelet de `wk-1` com `--cluster-dns` apontando para IP errado | kubelet funcionando, node Ready |
| `11-static-pod` | Static pod ausente | manifest do pod de monitoramento removido do control plane | pod `monitor-cp-1` Running em kube-system |

---

## Services & Networking — 20% do exame (4 cenários)

> Referência: [`labs/03-services-networking.md`](03-services-networking.md)

| ID | Título | O que está quebrado | O que você precisa entregar |
|---|---|---|---|
| `12-svc-no-endpoints` | Service sem endpoints | seletor do Service não bate com os labels dos pods | endpoints preenchidos, acesso funcionando |
| `13-netpol-blocking` | NetworkPolicy bloqueando tráfego | política nega acesso legítimo do `frontend` ao `backend` | comunicação restaurada sem remover a policy |
| `14-dns-broken` | DNS não resolve | CoreDNS com ConfigMap corrompido | pods conseguem resolver `kubernetes.default` |
| `15-ingress-wrong` | Ingress com backend errado | Ingress aponta para service inexistente | Ingress retornando 200 para o path correto |

---

## Workloads & Scheduling — 15% do exame (3 cenários)

> Referência: [`labs/02-workloads-scheduling.md`](02-workloads-scheduling.md)

| ID | Título | O que está quebrado / incompleto | O que você precisa entregar |
|---|---|---|---|
| `16-pod-pending-taint` | Pod preso por taint | node `wk-3` tem taint `env=prod:NoSchedule`, pod sem toleration | pod Running em `wk-3` |
| `17-pod-pending-resources` | Pod preso por resources | pod solicita 8 CPUs (mais que qualquer node tem disponível) | pod Running com requests ajustados |
| `18-wrong-image` | Deployment com imagem errada | tag `nginx:BROKEN` inexistente no registry | deployment Running com imagem correta |

---

## Storage — 10% do exame (2 cenários)

> Referência: [`labs/04-storage.md`](04-storage.md)

| ID | Título | O que está quebrado | O que você precisa entregar |
|---|---|---|---|
| `19-pvc-pending` | PVC preso em Pending | PVC solicita `ReadWriteMany` mas só existe PV `ReadWriteOnce` | PVC Bound e pod usando o volume |
| `20-pod-volume-wrong` | Dados não persistem | pod monta o volume em `/cache` mas a app escreve em `/data` | dados presentes em `/data` após reinício do pod |

---

## Resumo por dificuldade estimada

| Dificuldade | Cenários |
|---|---|
| Iniciante | 02, 03, 07, 17, 18 |
| Intermediário | 01, 04, 08, 09, 12, 13, 16, 19, 20 |
| Avançado | 05, 06, 10, 11, 14, 15 |

---

## Ordem de estudo sugerida

Começar pelo troubleshooting (maior peso) e ir para os demais:

```
01 → 02 → 03 → 05    (nodes e pods quebrados)
07 → 08 → 09         (RBAC e etcd)
12 → 13              (networking)
16 → 17 → 18         (scheduling)
19 → 20              (storage)
04 → 06 → 10 → 11 → 14 → 15   (avançados)
```
