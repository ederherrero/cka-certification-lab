# Lab 05 — Troubleshooting (30%)

> Domínio com maior peso no exame. Os cenários abaixo simulam falhas reais — pratique identificar e corrigir sem consultar a resposta primeiro.

Pré-requisito: cluster rodando (`python cka-lab.py up`) e kubectl configurado.

---

## Ferramentas essenciais de diagnóstico

```bash
# Uso de recursos em tempo real
kubectl top nodes
kubectl top pods --all-namespaces

# Eventos do cluster (ordenados por tempo)
kubectl get events --sort-by='.lastTimestamp' --all-namespaces

# Logs de um container
kubectl logs <pod> [-c <container>]
kubectl logs <pod> --previous          # container que crashou
kubectl logs <pod> -f --tail=50        # streaming em tempo real

# Inspecionar um pod
kubectl describe pod <nome>            # Events: seção mais importante
kubectl get pod <nome> -o yaml         # spec completa

# Executar comandos dentro de um pod
kubectl exec -it <pod> -- bash
kubectl exec -it <pod> -c <container> -- sh

# Pod de debug temporário no mesmo namespace
kubectl run debug --image=busybox:1.36 --rm -it --restart=Never -- sh
```

---

## 5.1 Diagnóstico de nodes

### Node em NotReady

```bash
# Ver status de todos os nodes
kubectl get nodes
kubectl describe node <nome>  # seção Conditions e Events

# SSH no node problemático
vagrant ssh wk-1

# Verificar o kubelet
systemctl status kubelet
journalctl -u kubelet -n 100 --no-pager

# Problemas comuns:
# - kubelet parado        → sudo systemctl start kubelet
# - disco cheio           → df -h /
# - memória insuficiente  → free -m
# - /etc/kubernetes/kubelet.conf corrompido → reconfigurar

# Reiniciar kubelet
sudo systemctl restart kubelet
sudo systemctl enable kubelet

# Verificar container runtime
sudo systemctl status containerd
sudo crictl ps       # listar containers em execução
sudo crictl images   # listar imagens
```

### Simular falha e recuperar

```bash
# No node wk-1: parar o kubelet
vagrant ssh wk-1 -- sudo systemctl stop kubelet

# Observar do host
kubectl get nodes -w  # wk-1 vai para NotReady em ~40s

# Restaurar
vagrant ssh wk-1 -- sudo systemctl start kubelet
kubectl get nodes -w  # volta para Ready
```

---

## 5.2 Diagnóstico de componentes do control plane

```bash
# Verificar componentes do control plane
kubectl get pods -n kube-system
kubectl get componentstatuses  # deprecated mas ainda útil

# Componentes estáticos (gerenciados pelo kubelet, não pelo API server)
vagrant ssh cp-1
ls /etc/kubernetes/manifests/
# apiserver.yaml, controller-manager.yaml, scheduler.yaml, etcd.yaml

# Se um componente estiver com problema, editar o manifest e o kubelet recria:
sudo vim /etc/kubernetes/manifests/kube-apiserver.yaml
# Após salvar, o kubelet detecta a mudança e recria o pod automaticamente

# Ver logs do API server
kubectl logs kube-apiserver-cka-certification-lab-cp-1 -n kube-system | tail -30

# Ver logs do etcd
kubectl logs etcd-cka-certification-lab-cp-1 -n kube-system | tail -30
```

### Simular falha do scheduler

```bash
# Mover o manifest para fora do diretório de static pods
vagrant ssh cp-1
sudo mv /etc/kubernetes/manifests/kube-scheduler.yaml /tmp/

# Criar um pod — ficará Pending porque não há scheduler
kubectl run pending-pod --image=nginx:1.25
kubectl get pod pending-pod  # Status: Pending

# Restaurar o scheduler
vagrant ssh cp-1 -- sudo mv /tmp/kube-scheduler.yaml /etc/kubernetes/manifests/
kubectl get pod pending-pod -w  # vai para Running após o scheduler reiniciar
```

---

## 5.3 Pods com problema — CrashLoopBackOff, ImagePullBackOff, OOMKilled

### CrashLoopBackOff

```bash
# Simular: container que sai imediatamente
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: crash-pod
spec:
  containers:
  - name: app
    image: busybox:1.36
    command: ["sh", "-c", "exit 1"]  # sai com erro
EOF

kubectl get pod crash-pod  # CrashLoopBackOff
kubectl logs crash-pod --previous   # ver logs da última execução
kubectl describe pod crash-pod      # seção Events mostra o exit code

# Diagnóstico:
# 1. Ver exit code em describe → "Exit Code: 1"
# 2. Ver logs com --previous
# 3. Verificar o comando e args do container
# 4. Checar se a configuração (ConfigMap, Secret, env) está correta
```

### ImagePullBackOff

```bash
# Simular: imagem inexistente
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: bad-image-pod
spec:
  containers:
  - name: app
    image: nginx:imagem-que-nao-existe
EOF

kubectl get pod bad-image-pod  # ImagePullBackOff ou ErrImagePull
kubectl describe pod bad-image-pod  # Events: "Failed to pull image"

# Causas comuns:
# 1. Tag incorreta                → corrigir o campo image
# 2. Registry privado sem secret  → criar ImagePullSecret
# 3. Node sem acesso à internet   → verificar DNS e proxy
# 4. Typo no nome da imagem       → kubectl set image pod/... <container>=<imagem-correta>
```

### OOMKilled

```bash
# Simular: container que consome mais memória que o limit
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: oom-pod
spec:
  containers:
  - name: app
    image: polinux/stress
    command: ["stress", "--vm", "1", "--vm-bytes", "200M"]
    resources:
      limits:
        memory: "50Mi"  # muito baixo para 200MB
EOF

kubectl get pod oom-pod -w  # OOMKilled → CrashLoopBackOff
kubectl describe pod oom-pod | grep -A3 "Last State\|OOM\|Exit Code"

# Solução: aumentar o memory limit ou reduzir o consumo da aplicação
```

---

## 5.4 Diagnóstico de aplicações

```bash
# Pod em Pending — motivos comuns:
kubectl describe pod <nome> | grep -A10 "Events"
# - Insufficient cpu/memory → node sem recursos
# - node(s) had taint → falta toleration
# - no nodes matched node affinity → label não existe no node
# - Unschedulable (node com taint NoSchedule) → adicionar toleration ou remover taint

# Pod Running mas aplicação não responde:
kubectl exec -it <pod> -- wget -qO- localhost:8080
kubectl logs <pod> --tail=50

# Ver variáveis de ambiente dentro do pod
kubectl exec <pod> -- env | sort

# Ver arquivos montados (ConfigMap/Secret)
kubectl exec <pod> -- ls /etc/config/
kubectl exec <pod> -- cat /etc/config/app.properties
```

---

## 5.5 Troubleshooting de networking

```bash
# Service sem endpoints — seletor errado
kubectl get svc web -o yaml | grep selector -A5
kubectl get pods --show-labels | grep <expected-label>

# Se o seletor não bate com nenhum pod, editar o service:
kubectl edit service web

# DNS não resolve
kubectl exec <pod> -- nslookup kubernetes.default
kubectl exec <pod> -- cat /etc/resolv.conf

# Se o DNS falha, verificar o CoreDNS
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl logs -n kube-system -l k8s-app=kube-dns | tail -20

# Conectividade pod-to-pod (mesma network Calico)
kubectl exec <pod-a> -- ping <ip-pod-b>

# Se o Calico estiver com problema:
kubectl get pods -n kube-system -l k8s-app=calico-node
kubectl logs -n kube-system <calico-pod> | tail -20

# NetworkPolicy bloqueando?
kubectl get networkpolicies --all-namespaces
# Testar removendo temporariamente a policy para confirmar o diagnóstico
```

---

## 5.6 Cenário completo — debug de uma aplicação quebrada

**Situação:** a equipe reportou que a aplicação `frontend` não consegue conectar ao banco de dados.

```bash
# Criar o cenário quebrado
kubectl create namespace broken-app

kubectl run frontend -n broken-app --image=busybox:1.36 \
  --labels=app=frontend \
  -- sh -c "while true; do wget -qO- http://db-service 2>&1 | head -1; sleep 5; done"

kubectl run db -n broken-app --image=nginx:1.25 --labels=app=database

# Service com seletor ERRADO (bug proposital)
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: db-service
  namespace: broken-app
spec:
  selector:
    app: db        # ERRADO: o pod tem label app=database
  ports:
  - port: 80
EOF
```

**Agora diagnostique:**

```bash
# 1. Ver os logs do frontend
kubectl logs -n broken-app frontend

# 2. Verificar se o service tem endpoints
kubectl get endpoints db-service -n broken-app

# 3. Comparar o seletor do service com os labels dos pods
kubectl describe svc db-service -n broken-app
kubectl get pods -n broken-app --show-labels

# 4. Corrigir o seletor
kubectl patch service db-service -n broken-app \
  -p '{"spec":{"selector":{"app":"database"}}}'

# 5. Verificar que o endpoint apareceu
kubectl get endpoints db-service -n broken-app

# 6. Confirmar que o frontend consegue conectar
kubectl logs -n broken-app frontend --tail=5
```

---

## 5.7 Diagnóstico de volumes

```bash
# Pod preso em ContainerCreating por PVC não bound
kubectl describe pod <nome>
# Events: "Unable to attach or mount volumes: ... waiting for PVC"

# Verificar o PVC
kubectl get pvc
kubectl describe pvc <nome>
# Possíveis causas:
# - Nenhum PV disponível que satisfaça os requisitos
# - StorageClass não existe
# - AccessMode incompatível

# PV e PVC existem mas não fazem bind?
kubectl get pv
kubectl describe pv <nome>
# Verificar: capacity, accessModes, storageClassName, status

# Verificar se o node tem o diretório do hostPath (se for esse o tipo)
vagrant ssh <node> -- ls /mnt/data
```

---

## 5.8 Monitorar uso de recursos

```bash
# Uso atual de CPU e memória por node
kubectl top nodes

# Uso por pod (todos os namespaces)
kubectl top pods --all-namespaces --sort-by=memory

# Pods com alto consumo de CPU
kubectl top pods --all-namespaces --sort-by=cpu | head -10

# Ver requests e limits configurados
kubectl describe nodes | grep -A5 "Allocated resources"

# Quota usada por namespace
kubectl describe resourcequota -n <namespace>
```

---

## Guia rápido de comandos para o exame

```bash
# Aliases recomendados — configure no início do exame
alias k=kubectl
export do='--dry-run=client -o yaml'
export now='--grace-period=0 --force'

# Gerar YAML sem aplicar
k run pod-name --image=nginx:1.25 $do

# Deletar imediatamente sem esperar
k delete pod pod-name $now

# Ver API fields disponíveis
k explain pod.spec.containers
k explain deployment.spec.strategy

# Buscar recursos com label
k get pods -l app=web --all-namespaces

# Ver todos os recursos de um namespace
k get all -n kube-system

# Checar permissões de um ServiceAccount
k auth can-i get pods --as=system:serviceaccount:dev:dev-user -n dev
```

---

## Limpeza

```bash
kubectl delete pod crash-pod bad-image-pod oom-pod pending-pod 2>/dev/null || true
kubectl delete namespace broken-app 2>/dev/null || true
```
