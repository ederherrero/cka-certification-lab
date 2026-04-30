# Lab 01 — Cluster Architecture, Installation & Configuration (25%)

Pré-requisito: cluster rodando (`python cka-lab.py up`) e kubectl configurado.

---

## 1.1 Inspecionar os componentes do cluster

### Objetivo
Entender quais componentes existem no control plane e como identificá-los.

```bash
# Listar todos os pods do control plane
kubectl get pods -n kube-system

# Verificar os componentes estáticos (rodam como static pods)
kubectl get pods -n kube-system -l tier=control-plane

# Inspecionar o API server
kubectl describe pod kube-apiserver-cka-certification-lab-cp-1 -n kube-system

# Ver configuração do scheduler
kubectl describe pod kube-scheduler-cka-certification-lab-cp-1 -n kube-system

# Ver configuração do controller-manager
kubectl describe pod kube-controller-manager-cka-certification-lab-cp-1 -n kube-system
```

```bash
# Verificar o etcd
kubectl describe pod etcd-cka-certification-lab-cp-1 -n kube-system

# Onde ficam os manifests dos static pods?
vagrant ssh cp-1
ls /etc/kubernetes/manifests/
```

**O que observar:** os static pods são gerenciados diretamente pelo kubelet, não pelo API server. Se você editar os arquivos em `/etc/kubernetes/manifests/`, o kubelet recria o pod automaticamente.

---

## 1.2 Verificar o estado dos nodes e do kubelet

```bash
# Ver nodes e suas condições
kubectl get nodes
kubectl describe node cka-certification-lab-cp-1

# SSH no node e verificar o kubelet
vagrant ssh wk-1
systemctl status kubelet
journalctl -u kubelet -n 50
```

---

## 1.3 RBAC — Role-Based Access Control

### Objetivo
Criar um usuário com acesso restrito a um namespace.

```bash
# Criar namespace de teste
kubectl create namespace dev

# Criar uma Role que permite get/list/watch em pods
kubectl create role pod-reader \
  --verb=get,list,watch \
  --resource=pods \
  --namespace=dev

# Criar um ServiceAccount
kubectl create serviceaccount dev-user --namespace=dev

# Vincular a Role ao ServiceAccount
kubectl create rolebinding dev-user-binding \
  --role=pod-reader \
  --serviceaccount=dev:dev-user \
  --namespace=dev

# Verificar o que o dev-user pode fazer
kubectl auth can-i get pods --namespace=dev --as=system:serviceaccount:dev:dev-user
kubectl auth can-i delete pods --namespace=dev --as=system:serviceaccount:dev:dev-user
kubectl auth can-i get pods --namespace=default --as=system:serviceaccount:dev:dev-user
```

**Resultado esperado:** `yes`, `no`, `no`

```bash
# Listar todas as permissões de um serviceaccount
kubectl auth can-i --list --namespace=dev --as=system:serviceaccount:dev:dev-user
```

### ClusterRole — acesso em todos os namespaces

```bash
# Criar ClusterRole para leitura de nodes
kubectl create clusterrole node-reader \
  --verb=get,list,watch \
  --resource=nodes

# Vincular ao serviceaccount dev-user
kubectl create clusterrolebinding dev-user-node-binding \
  --clusterrole=node-reader \
  --serviceaccount=dev:dev-user

kubectl auth can-i get nodes --as=system:serviceaccount:dev:dev-user
```

---

## 1.4 Backup e Restore do etcd

> Cai com frequência no exame. Pratique até memorizar os comandos.

```bash
# SSH no control plane
vagrant ssh cp-1

# Verificar onde o etcd está ouvindo
sudo cat /etc/kubernetes/manifests/etcd.yaml | grep -E 'listen-client|cert|key|trusted'

# Fazer backup do etcd
sudo ETCDCTL_API=3 etcdctl snapshot save /tmp/etcd-backup.db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key

# Verificar o backup
sudo ETCDCTL_API=3 etcdctl snapshot status /tmp/etcd-backup.db --write-out=table
```

```bash
# Simular restore (em um ambiente de teste)
sudo ETCDCTL_API=3 etcdctl snapshot restore /tmp/etcd-backup.db \
  --data-dir=/var/lib/etcd-restore

# Atualizar o manifest do etcd para apontar para o novo data-dir
sudo sed -i 's|/var/lib/etcd|/var/lib/etcd-restore|' /etc/kubernetes/manifests/etcd.yaml

# Aguardar o etcd reiniciar (pode levar 30-60s)
watch kubectl get nodes
```

---

## 1.5 Upgrade do cluster com kubeadm

> No exame você tipicamente faz upgrade de uma versão minor (ex: 1.32 → 1.33).

```bash
# Ver versão atual
kubectl version
kubeadm version

# No control plane
vagrant ssh cp-1

# Ver versões disponíveis
sudo apt-cache policy kubeadm | head -20

# Planejar o upgrade
sudo kubeadm upgrade plan

# Executar upgrade do control plane (substitua pela versão alvo)
sudo kubeadm upgrade apply v1.34.7

# Drain o control plane
kubectl drain cka-certification-lab-cp-1 --ignore-daemonsets

# Atualizar kubelet e kubectl no control plane
sudo apt-get install -y kubelet=1.34.7-1.1 kubectl=1.34.7-1.1
sudo systemctl daemon-reload && sudo systemctl restart kubelet

# Uncordon o control plane
kubectl uncordon cka-certification-lab-cp-1
```

```bash
# Para cada worker — drain → upgrade → uncordon
kubectl drain cka-certification-lab-wk-1 --ignore-daemonsets --delete-emptydir-data

vagrant ssh wk-1
sudo kubeadm upgrade node
sudo apt-get install -y kubelet=1.34.7-1.1
sudo systemctl daemon-reload && sudo systemctl restart kubelet
exit

kubectl uncordon cka-certification-lab-wk-1
kubectl get nodes
```

---

## 1.6 Helm — Instalar uma aplicação

```bash
# Instalar Helm (se não tiver)
# Windows: https://helm.sh/docs/intro/install/

# Adicionar repositório e instalar nginx-ingress como exemplo
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

# Ver o que seria instalado (dry-run)
helm install my-ingress ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --dry-run

# Instalar de fato
helm install my-ingress ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace

# Verificar
helm list -n ingress-nginx
kubectl get pods -n ingress-nginx

# Remover
helm uninstall my-ingress -n ingress-nginx
```

---

## 1.7 Kustomize — Customizar manifests

```bash
# Criar estrutura base
mkdir -p /tmp/kustomize-lab/base
mkdir -p /tmp/kustomize-lab/overlays/dev
mkdir -p /tmp/kustomize-lab/overlays/prod

cat <<EOF > /tmp/kustomize-lab/base/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: my-app
        image: nginx:1.25
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
EOF

cat <<EOF > /tmp/kustomize-lab/base/kustomization.yaml
resources:
  - deployment.yaml
EOF

cat <<EOF > /tmp/kustomize-lab/overlays/dev/kustomization.yaml
bases:
  - ../../base
patches:
  - patch: |-
      - op: replace
        path: /spec/replicas
        value: 1
namePrefix: dev-
EOF

cat <<EOF > /tmp/kustomize-lab/overlays/prod/kustomization.yaml
bases:
  - ../../base
patches:
  - patch: |-
      - op: replace
        path: /spec/replicas
        value: 3
namePrefix: prod-
EOF

# Ver o que seria aplicado
kubectl kustomize /tmp/kustomize-lab/overlays/dev
kubectl kustomize /tmp/kustomize-lab/overlays/prod

# Aplicar
kubectl apply -k /tmp/kustomize-lab/overlays/dev
kubectl get deployments
```

---

## Limpeza

```bash
kubectl delete namespace dev
kubectl delete clusterrole node-reader
kubectl delete clusterrolebinding dev-user-node-binding
kubectl delete -k /tmp/kustomize-lab/overlays/dev 2>/dev/null || true
```
