# Lab 03 — Services & Networking (20%)

Pré-requisito: cluster rodando (`python cka-lab.py up`) e kubectl configurado.

---

## 3.1 Services — ClusterIP, NodePort e LoadBalancer

```bash
# Criar deployment de teste
kubectl create deployment web --image=nginx:1.25 --replicas=2

# ClusterIP (padrão) — acessível somente de dentro do cluster
kubectl expose deployment web --port=80 --target-port=80 --name=web-clusterip
kubectl get service web-clusterip

# Testar de dentro do cluster
kubectl run test --image=busybox:1.36 --rm -it --restart=Never -- \
  wget -qO- web-clusterip

# NodePort — acessível do host na porta do node
kubectl expose deployment web --port=80 --target-port=80 \
  --type=NodePort --name=web-nodeport
kubectl get service web-nodeport

# Ver qual porta foi alocada (30000-32767)
NODE_PORT=$(kubectl get svc web-nodeport -o jsonpath='{.spec.ports[0].nodePort}')
echo "Acessar em: http://192.168.99.11:$NODE_PORT"
```

```bash
# ExternalName — apelido para DNS externo
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: external-db
spec:
  type: ExternalName
  externalName: mydb.example.com
EOF

# Pods que usam "external-db" terão o DNS resolvido para mydb.example.com
```

---

## 3.2 Endpoints e EndpointSlices

```bash
# Ver os endpoints de um service
kubectl get endpoints web-clusterip
kubectl describe endpoints web-clusterip

# EndpointSlices (substituem endpoints em clusters maiores)
kubectl get endpointslices -l kubernetes.io/service-name=web-clusterip

# Service sem selector — endpoints manuais (útil para serviços externos)
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: manual-svc
spec:
  ports:
  - port: 80
    protocol: TCP
---
apiVersion: v1
kind: Endpoints
metadata:
  name: manual-svc
subsets:
- addresses:
  - ip: 192.168.99.10    # IP de um node real como exemplo
  ports:
  - port: 80
EOF
```

---

## 3.3 Ingress Controller e Ingress Resources

```bash
# Instalar ingress-nginx (se não tiver Helm, use o manifesto direto)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.0/deploy/static/provider/baremetal/deploy.yaml

# Aguardar o controller ficar pronto
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s

# Criar dois serviços para o Ingress rotear
kubectl create deployment app-v1 --image=nginx:1.25
kubectl create deployment app-v2 --image=nginx:1.26

kubectl expose deployment app-v1 --port=80
kubectl expose deployment app-v2 --port=80
```

```bash
# Ingress baseado em path
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: path-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
  - host: myapp.local
    http:
      paths:
      - path: /v1
        pathType: Prefix
        backend:
          service:
            name: app-v1
            port:
              number: 80
      - path: /v2
        pathType: Prefix
        backend:
          service:
            name: app-v2
            port:
              number: 80
EOF

kubectl get ingress path-ingress

# Testar (adicione myapp.local no /etc/hosts apontando para o IP do node)
# curl http://myapp.local:<nodeport-do-ingress>/v1
```

---

## 3.4 Gateway API (novo em 2025)

> A Gateway API substitui gradualmente o Ingress. O exame CKA 2025 cobra conhecimento básico.

```bash
# Verificar se os CRDs da Gateway API estão instalados
kubectl get crd gateways.gateway.networking.k8s.io 2>/dev/null && \
  echo "Gateway API instalada" || echo "Gateway API não instalada"

# Instalar os CRDs da Gateway API (standard channel)
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.0/standard-install.yaml

# Conceitos principais:
# GatewayClass — define o tipo de gateway (criado pelo cluster admin)
# Gateway       — instância do gateway (porta, protocolo)
# HTTPRoute     — regras de roteamento HTTP

cat <<EOF | kubectl apply -f -
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: example-class
spec:
  controllerName: example.com/foo-controller  # substitua pelo controller instalado
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: example-gateway
spec:
  gatewayClassName: example-class
  listeners:
  - name: http
    protocol: HTTP
    port: 80
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: example-route
spec:
  parentRefs:
  - name: example-gateway
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /
    backendRefs:
    - name: web-clusterip
      port: 80
EOF
```

**Diferenças principais Ingress × Gateway API:**

| | Ingress | Gateway API |
|---|---|---|
| Recurso de roteamento | Ingress | HTTPRoute, GRPCRoute |
| Controle de porta/protocolo | anotações | Gateway spec |
| Multi-tenant | limitado | GatewayClass por equipe |
| Status | estável há anos | stable desde 1.0 (2023) |

---

## 3.5 Network Policies — restringir tráfego

```bash
kubectl create namespace netpol-lab

# Criar pods de teste
kubectl run frontend --image=nginx:1.25 -n netpol-lab --labels=role=frontend
kubectl run backend --image=nginx:1.25 -n netpol-lab --labels=role=backend
kubectl run db --image=nginx:1.25 -n netpol-lab --labels=role=db

kubectl expose pod frontend --port=80 -n netpol-lab
kubectl expose pod backend --port=80 -n netpol-lab
kubectl expose pod db --port=80 -n netpol-lab

# Sem NetworkPolicy: tráfego livre entre todos
kubectl exec -n netpol-lab frontend -- wget -qO- http://db
```

```bash
# NetworkPolicy — nega tudo por padrão para o DB, só backend pode acessar
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-policy
  namespace: netpol-lab
spec:
  podSelector:
    matchLabels:
      role: db
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: backend
    ports:
    - protocol: TCP
      port: 80
EOF

# Testar: backend pode acessar db
kubectl exec -n netpol-lab backend -- wget -qO- --timeout=3 http://db
# Resultado esperado: HTML do nginx

# Testar: frontend NÃO pode acessar db
kubectl exec -n netpol-lab frontend -- wget -qO- --timeout=3 http://db
# Resultado esperado: timeout (connection refused)
```

```bash
# Egress — restringir tráfego de saída
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-egress
  namespace: netpol-lab
spec:
  podSelector:
    matchLabels:
      role: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          role: backend
    ports:
    - protocol: TCP
      port: 80
  - ports:                # DNS (obrigatório para resolver nomes)
    - protocol: UDP
      port: 53
EOF
```

---

## 3.6 CoreDNS — resolução de nomes

```bash
# Verificar o CoreDNS
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl get configmap coredns -n kube-system -o yaml

# Formato do DNS interno:
# <service>.<namespace>.svc.cluster.local
# <pod-ip-com-hifens>.<namespace>.pod.cluster.local

# Testar resolução DNS de dentro de um pod
kubectl run dns-test --image=busybox:1.36 --rm -it --restart=Never -- \
  sh -c "nslookup kubernetes.default.svc.cluster.local && \
         nslookup web-clusterip.default.svc.cluster.local"

# Ver o arquivo /etc/resolv.conf de um pod
kubectl exec dns-test -- cat /etc/resolv.conf 2>/dev/null || \
  kubectl run dns2 --image=busybox:1.36 --rm -it --restart=Never -- cat /etc/resolv.conf
```

```bash
# Adicionar entrada personalizada no CoreDNS (host stub)
kubectl edit configmap coredns -n kube-system
# Adicionar dentro do bloco Corefile:
# myapp.company.com:53 {
#   hosts {
#     192.168.1.100 myapp.company.com
#     fallthrough
#   }
# }

# Após editar, reiniciar o CoreDNS para aplicar
kubectl rollout restart deployment coredns -n kube-system
```

---

## 3.7 Troubleshooting de rede (prévia do Lab 05)

```bash
# Service não tem endpoints? O seletor pode estar errado
kubectl get endpoints <service-name>
kubectl describe service <service-name>  # ver Selector
kubectl get pods --show-labels           # comparar labels

# DNS não resolve dentro do pod
kubectl exec <pod> -- nslookup kubernetes
kubectl exec <pod> -- cat /etc/resolv.conf

# Conectividade pod-to-pod
kubectl exec <pod-a> -- ping <ip-do-pod-b>
kubectl exec <pod-a> -- wget -qO- http://<ip-do-pod-b>:<porta>

# NetworkPolicy bloqueando?
kubectl get networkpolicies --all-namespaces
kubectl describe networkpolicy <nome>
```

---

## Limpeza

```bash
kubectl delete deployment web app-v1 app-v2
kubectl delete service web-clusterip web-nodeport external-db manual-svc app-v1 app-v2
kubectl delete ingress path-ingress
kubectl delete namespace netpol-lab
kubectl delete -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.0/deploy/static/provider/baremetal/deploy.yaml 2>/dev/null || true
kubectl delete endpoints manual-svc 2>/dev/null || true
```
