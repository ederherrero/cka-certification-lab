# Lab 02 — Workloads & Scheduling (15%)

Pré-requisito: cluster rodando (`python cka-lab.py up`) e kubectl configurado.

---

## 2.1 Deployments — criar, escalar e fazer rollback

```bash
# Criar deployment
kubectl create deployment web --image=nginx:1.25 --replicas=3

# Ver o deployment e os pods
kubectl get deployment web
kubectl get pods -l app=web

# Escalar
kubectl scale deployment web --replicas=5
kubectl get pods -l app=web

# Atualizar a imagem (gera um novo rollout)
kubectl set image deployment/web nginx=nginx:1.26

# Acompanhar o rollout
kubectl rollout status deployment/web

# Ver histórico de revisões
kubectl rollout history deployment/web

# Fazer rollback para a revisão anterior
kubectl rollout undo deployment/web

# Rollback para uma revisão específica
kubectl rollout undo deployment/web --to-revision=1
```

```bash
# Ver detalhes do rollout (estratégia RollingUpdate)
kubectl describe deployment web | grep -A5 "Strategy"

# Editar estratégia de atualização
kubectl patch deployment web -p '{"spec":{"strategy":{"rollingUpdate":{"maxSurge":1,"maxUnavailable":0}}}}'
```

---

## 2.2 StatefulSets — workloads com identidade estável

```bash
# Criar um StatefulSet com headless service
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: nginx-headless
spec:
  clusterIP: None
  selector:
    app: nginx-sts
  ports:
  - port: 80
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: nginx-sts
spec:
  serviceName: nginx-headless
  replicas: 3
  selector:
    matchLabels:
      app: nginx-sts
  template:
    metadata:
      labels:
        app: nginx-sts
    spec:
      containers:
      - name: nginx
        image: nginx:1.25
        volumeMounts:
        - name: data
          mountPath: /usr/share/nginx/html
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 100Mi
EOF

# Observar a criação ordenada (0, 1, 2)
kubectl get pods -w -l app=nginx-sts

# Os pods têm identidade estável: nginx-sts-0, nginx-sts-1, nginx-sts-2
# O DNS interno: nginx-sts-0.nginx-headless.default.svc.cluster.local
kubectl exec nginx-sts-0 -- hostname
```

---

## 2.3 DaemonSets — um pod por node

```bash
# DaemonSet roda em todos os nodes (inclusive no control plane com toleração)
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: log-agent
  namespace: kube-system
spec:
  selector:
    matchLabels:
      app: log-agent
  template:
    metadata:
      labels:
        app: log-agent
    spec:
      tolerations:
      - key: node-role.kubernetes.io/control-plane
        effect: NoSchedule
      containers:
      - name: agent
        image: busybox:1.36
        command: ["sh", "-c", "while true; do echo 'log'; sleep 30; done"]
        resources:
          requests:
            cpu: "10m"
            memory: "20Mi"
EOF

# Verificar — deve ter um pod em cada node
kubectl get daemonset log-agent -n kube-system
kubectl get pods -n kube-system -l app=log-agent -o wide
```

---

## 2.4 Jobs e CronJobs

```bash
# Job — executa uma tarefa e termina
kubectl create job pi --image=perl:5.34 -- perl -Mbignum=bpi -wle 'print bpi(100)'
kubectl get job pi
kubectl logs job/pi

# Job com múltiplas execuções paralelas
cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: parallel-job
spec:
  completions: 6
  parallelism: 2
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: worker
        image: busybox:1.36
        command: ["sh", "-c", "echo Processing; sleep 5"]
EOF

kubectl get job parallel-job -w
```

```bash
# CronJob — executa em agendamento
kubectl create cronjob hello \
  --image=busybox:1.36 \
  --schedule="*/1 * * * *" \
  -- sh -c 'date; echo Hello'

# Aguardar o primeiro disparo (~1 min) e ver os jobs criados
kubectl get cronjob hello
kubectl get jobs --watch

# Ver logs do job mais recente
kubectl logs job/$(kubectl get jobs -l "app=hello" --sort-by=.metadata.creationTimestamp -o name | tail -1 | sed 's|job.batch/||')
```

---

## 2.5 Resource Requests e Limits

```bash
# Pod com requests e limits definidos
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: resource-demo
spec:
  containers:
  - name: app
    image: nginx:1.25
    resources:
      requests:
        memory: "64Mi"
        cpu: "100m"
      limits:
        memory: "128Mi"
        cpu: "500m"
EOF

# Ver o que foi alocado
kubectl describe pod resource-demo | grep -A6 "Requests\|Limits"

# Pod consumindo mais memória que o limit é killed com OOMKilled
# (simulação — observe o campo reason no status)
kubectl get pod resource-demo -o jsonpath='{.status.containerStatuses[0].state}'
```

---

## 2.6 LimitRange e ResourceQuota

```bash
kubectl create namespace quota-lab

# LimitRange — define defaults e máximos por container
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: LimitRange
metadata:
  name: default-limits
  namespace: quota-lab
spec:
  limits:
  - type: Container
    default:
      cpu: "200m"
      memory: "128Mi"
    defaultRequest:
      cpu: "100m"
      memory: "64Mi"
    max:
      cpu: "1"
      memory: "512Mi"
EOF

# ResourceQuota — limita o total do namespace
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ResourceQuota
metadata:
  name: ns-quota
  namespace: quota-lab
spec:
  hard:
    pods: "10"
    requests.cpu: "2"
    requests.memory: "2Gi"
    limits.cpu: "4"
    limits.memory: "4Gi"
EOF

# Ver os limites aplicados
kubectl describe limitrange default-limits -n quota-lab
kubectl describe resourcequota ns-quota -n quota-lab

# Criar pod no namespace (herda defaults do LimitRange)
kubectl run nginx --image=nginx:1.25 -n quota-lab
kubectl describe pod nginx -n quota-lab | grep -A6 "Requests\|Limits"
```

---

## 2.7 Node Selectors e Node Affinity

```bash
# Adicionar label a um worker
kubectl label node cka-certification-lab-wk-1 disk=ssd
kubectl get nodes --show-labels | grep disk

# NodeSelector — força scheduling no node com o label
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: ssd-pod
spec:
  nodeSelector:
    disk: ssd
  containers:
  - name: app
    image: nginx:1.25
EOF

kubectl get pod ssd-pod -o wide  # deve estar em wk-1
```

```bash
# Node Affinity — mais expressivo que nodeSelector
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: affinity-pod
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: disk
            operator: In
            values: [ssd]
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 1
        preference:
          matchExpressions:
          - key: zone
            operator: In
            values: [us-east-1a]
  containers:
  - name: app
    image: nginx:1.25
EOF
```

---

## 2.8 Taints e Tolerations

```bash
# Ver taints existentes (control-plane tem taint por padrão)
kubectl describe node cka-certification-lab-cp-1 | grep Taint

# Adicionar taint a um worker
kubectl taint node cka-certification-lab-wk-2 dedicated=gpu:NoSchedule

# Pod sem toleration não vai para wk-2
kubectl run no-gpu --image=nginx:1.25
kubectl get pod no-gpu -o wide  # vai para outro node

# Pod com toleration pode ser agendado em wk-2
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  tolerations:
  - key: dedicated
    operator: Equal
    value: gpu
    effect: NoSchedule
  containers:
  - name: app
    image: nginx:1.25
EOF

# Remover o taint depois
kubectl taint node cka-certification-lab-wk-2 dedicated=gpu:NoSchedule-
```

---

## 2.9 ConfigMaps e Secrets

```bash
# ConfigMap via literal
kubectl create configmap app-config \
  --from-literal=ENV=production \
  --from-literal=LOG_LEVEL=info

# ConfigMap via arquivo
echo "server.port=8080" > /tmp/app.properties
kubectl create configmap app-properties --from-file=/tmp/app.properties

# Usar ConfigMap como env vars
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: config-pod
spec:
  containers:
  - name: app
    image: busybox:1.36
    command: ["sh", "-c", "env | grep -E 'ENV|LOG'; sleep 3600"]
    envFrom:
    - configMapRef:
        name: app-config
EOF

kubectl logs config-pod
```

```bash
# Secret (base64 automaticamente)
kubectl create secret generic db-secret \
  --from-literal=username=admin \
  --from-literal=password=supersecret

# Montar Secret como volume
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: secret-pod
spec:
  containers:
  - name: app
    image: busybox:1.36
    command: ["sh", "-c", "cat /etc/secrets/password; sleep 3600"]
    volumeMounts:
    - name: secret-vol
      mountPath: /etc/secrets
      readOnly: true
  volumes:
  - name: secret-vol
    secret:
      secretName: db-secret
EOF

kubectl exec secret-pod -- cat /etc/secrets/password
```

---

## 2.10 HPA — Horizontal Pod Autoscaler

```bash
# Requer metrics-server instalado
kubectl top nodes  # verifica se metrics-server está ok

# Deployment alvo
kubectl create deployment hpa-demo --image=nginx:1.25 --replicas=1
kubectl set resources deployment hpa-demo --requests=cpu=100m

# Criar HPA
kubectl autoscale deployment hpa-demo --cpu-percent=50 --min=1 --max=5

# Ver status do HPA
kubectl get hpa hpa-demo
kubectl describe hpa hpa-demo

# Para gerar carga (em outro terminal):
# kubectl run -i --tty load-gen --rm --image=busybox --restart=Never \
#   -- sh -c "while true; do wget -q -O- http://hpa-demo; done"
```

---

## Limpeza

```bash
kubectl delete deployment web hpa-demo
kubectl delete statefulset nginx-sts
kubectl delete service nginx-headless
kubectl delete daemonset log-agent -n kube-system
kubectl delete job pi parallel-job
kubectl delete cronjob hello
kubectl delete pod resource-demo ssd-pod affinity-pod no-gpu gpu-pod config-pod secret-pod
kubectl delete configmap app-config app-properties
kubectl delete secret db-secret
kubectl delete namespace quota-lab
kubectl label node cka-certification-lab-wk-1 disk-
kubectl delete hpa hpa-demo 2>/dev/null || true
```
