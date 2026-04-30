# Lab 04 — Storage (10%)

Pré-requisito: cluster rodando (`python cka-lab.py up`) e kubectl configurado.

---

## 4.1 Volumes efêmeros — emptyDir, configMap, secret, hostPath

```bash
# emptyDir — existe enquanto o pod viver, compartilhado entre containers
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: emptydir-demo
spec:
  containers:
  - name: writer
    image: busybox:1.36
    command: ["sh", "-c", "echo Hello > /shared/data.txt; sleep 3600"]
    volumeMounts:
    - name: shared
      mountPath: /shared
  - name: reader
    image: busybox:1.36
    command: ["sh", "-c", "sleep 3; cat /shared/data.txt; sleep 3600"]
    volumeMounts:
    - name: shared
      mountPath: /shared
  volumes:
  - name: shared
    emptyDir: {}
EOF

kubectl logs emptydir-demo -c reader
```

```bash
# hostPath — monta diretório do node (use com cautela)
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: hostpath-demo
spec:
  containers:
  - name: app
    image: busybox:1.36
    command: ["sh", "-c", "ls /node-logs; sleep 3600"]
    volumeMounts:
    - name: logs
      mountPath: /node-logs
  volumes:
  - name: logs
    hostPath:
      path: /var/log
      type: Directory
EOF

kubectl exec hostpath-demo -- ls /node-logs | head -5
```

---

## 4.2 PersistentVolumes (PV) — provisioning manual

```bash
# PV usa hostPath como backend (adequado para lab single-node; use NFS/CSI em produção)
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-demo
spec:
  capacity:
    storage: 1Gi
  accessModes:
  - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  hostPath:
    path: /mnt/data
EOF

kubectl get pv pv-demo
kubectl describe pv pv-demo
```

**Access Modes:**

| Modo | Abreviação | Descrição |
|---|---|---|
| ReadWriteOnce | RWO | um node de leitura/escrita |
| ReadOnlyMany | ROX | vários nodes somente leitura |
| ReadWriteMany | RWX | vários nodes de leitura/escrita |
| ReadWriteOncePod | RWOP | um único pod (k8s 1.22+) |

**Reclaim Policies:**

| Policy | Comportamento após PVC deletado |
|---|---|
| Retain | PV fica com dados, requer intervenção manual |
| Delete | PV e dados são apagados automaticamente |
| Recycle | Deprecado — limpa os dados e disponibiliza o PV novamente |

---

## 4.3 PersistentVolumeClaims (PVC)

```bash
# PVC solicita storage ao cluster
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pvc-demo
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 500Mi
EOF

# O PVC faz binding com o PV que satisfaça os requisitos
kubectl get pvc pvc-demo
kubectl get pv pv-demo  # Status muda de Available para Bound
```

```bash
# Pod usando o PVC
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: pvc-pod
spec:
  containers:
  - name: app
    image: busybox:1.36
    command: ["sh", "-c", "echo Persistido > /data/file.txt; cat /data/file.txt; sleep 3600"]
    volumeMounts:
    - name: storage
      mountPath: /data
  volumes:
  - name: storage
    persistentVolumeClaim:
      claimName: pvc-demo
EOF

kubectl logs pvc-pod
```

```bash
# Simular persistência: deletar e recriar o pod
kubectl delete pod pvc-pod
# Recriar com o mesmo PVC
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: pvc-pod
spec:
  containers:
  - name: app
    image: busybox:1.36
    command: ["sh", "-c", "cat /data/file.txt; sleep 3600"]
    volumeMounts:
    - name: storage
      mountPath: /data
  volumes:
  - name: storage
    persistentVolumeClaim:
      claimName: pvc-demo
EOF

kubectl logs pvc-pod  # "Persistido" ainda está lá
```

---

## 4.4 StorageClasses — provisioning dinâmico

```bash
# Ver StorageClasses disponíveis
kubectl get storageclass

# StorageClass com provisioner local (para lab)
cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: local-storage
  annotations:
    storageclass.kubernetes.io/is-default-class: "false"
provisioner: kubernetes.io/no-provisioner   # sem provisioner automático
volumeBindingMode: WaitForFirstConsumer      # aguarda pod ser criado antes de fazer bind
EOF

kubectl get storageclass
```

```bash
# Para provisioning dinâmico real, instale o local-path-provisioner (Rancher)
# Este é o mais simples para labs com kubeadm:
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.28/deploy/local-path-storage.yaml

# Verificar
kubectl get storageclass local-path
kubectl get pods -n local-path-storage

# PVC que usa provisioning dinâmico (cria o PV automaticamente)
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: dynamic-pvc
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: local-path
  resources:
    requests:
      storage: 200Mi
EOF

kubectl get pvc dynamic-pvc  # Status: Pending até um pod ser criado
kubectl get pv               # PV será criado automaticamente ao montar
```

---

## 4.5 Cenário completo — StatefulSet com storage dinâmico

```bash
# StatefulSet com volumeClaimTemplates cria um PVC por replica automaticamente
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: mysql-headless
spec:
  clusterIP: None
  selector:
    app: mysql
  ports:
  - port: 3306
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  serviceName: mysql-headless
  replicas: 1
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - name: mysql
        image: mysql:8.0
        env:
        - name: MYSQL_ROOT_PASSWORD
          value: "rootpass"
        volumeMounts:
        - name: mysql-data
          mountPath: /var/lib/mysql
  volumeClaimTemplates:
  - metadata:
      name: mysql-data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: local-path
      resources:
        requests:
          storage: 500Mi
EOF

# Aguardar o pod ficar Running
kubectl get pod mysql-0 -w

# Verificar o PVC criado automaticamente
kubectl get pvc mysql-data-mysql-0
kubectl get pv
```

---

## 4.6 CSI — Container Storage Interface

> CSI é o padrão de plugin de storage no Kubernetes. No exame, você precisa entender o conceito, não implementar um driver CSI do zero.

```bash
# Ver drivers CSI instalados
kubectl get csidrivers
kubectl get csinode

# CSI separa o storage em 3 operações:
# 1. Provision  — criar o volume no storage backend
# 2. Attach     — conectar o volume ao node
# 3. Mount      — montar o volume no pod

# Exemplos de drivers CSI comuns:
# - kubernetes.io/aws-ebs      → EBS na AWS
# - disk.csi.azure.com         → Azure Disk
# - pd.csi.storage.gke.io      → GKE Persistent Disk
# - rancher.io/local-path      → local-path-provisioner (lab)
# - rook-ceph.rbd.csi.ceph.com → Ceph RBD

# Ver detalhes de um CSI driver
kubectl describe csidriver rancher.io/local-path 2>/dev/null || \
  echo "local-path-provisioner não instalado"
```

---

## 4.7 Troubleshooting de storage

```bash
# Pod preso em Pending por causa de PVC?
kubectl describe pod <nome> | grep -A5 "Events"
# Mensagem comum: "0/5 nodes are available: waiting for first consumer..."
# ou: "no persistent volumes available for this claim"

# PVC preso em Pending?
kubectl describe pvc <nome>
# Verificar: selector correto? StorageClass existe? Capacity disponível?

# PV e PVC não fazem bind?
kubectl get pv
kubectl get pvc
# Verificar: accessModes compatíveis, storage suficiente, storageClassName igual

# PVC deletado mas PV ainda existe (Retain policy)?
# O PV fica em estado Released — precisa limpar os dados e remover o claimRef manualmente
kubectl edit pv <nome>
# Remover o campo: spec.claimRef
# Isso coloca o PV de volta em Available

# Ver eventos de storage
kubectl get events --sort-by='.lastTimestamp' | grep -i "volume\|pvc\|pv"
```

---

## Limpeza

```bash
kubectl delete pod emptydir-demo hostpath-demo pvc-pod
kubectl delete pvc pvc-demo dynamic-pvc
kubectl delete pv pv-demo 2>/dev/null || true
kubectl delete statefulset mysql
kubectl delete service mysql-headless
kubectl delete storageclass local-storage 2>/dev/null || true
kubectl delete pvc mysql-data-mysql-0 2>/dev/null || true
```
