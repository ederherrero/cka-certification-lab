from scenarios.helpers import kubectl, apply_yaml, delete_ns, exec_in_pod, wait_for

METADATA = {
    "id": "13-netpol-blocking",
    "title": "NetworkPolicy bloqueando tráfego legítimo",
    "category": "Networking",
    "lab_ref": "labs/03-services-networking.md",
    "difficulty": "avancado",
}

NS = "scenario-13"

DESCRIPTION = """\
╔══════════════════════════════════════════════════════════════════╗
║  CENÁRIO 13 — NetworkPolicy bloqueando tráfego legítimo          ║
╠══════════════════════════════════════════════════════════════════╣
║  O pod 'frontend' não consegue se comunicar com o pod 'backend'  ║
║  no namespace scenario-13. Uma NetworkPolicy foi aplicada recen- ║
║  temente e pode estar causando o problema.                       ║
║                                                                  ║
║  TAREFA                                                          ║
║  Corrija a NetworkPolicy 'backend-policy' para permitir que o    ║
║  pod 'frontend' acesse o pod 'backend' na porta 80.              ║
║  Não remova a NetworkPolicy — apenas corrija-a.                  ║
║                                                                  ║
║  Namespace: scenario-13                                          ║
╚══════════════════════════════════════════════════════════════════╝"""

HINT = """\
Dica 1: kubectl get networkpolicies -n scenario-13
        kubectl describe networkpolicy backend-policy -n scenario-13
        Leia o campo 'PodSelector' e 'Ingress'.

Dica 2: O pod frontend tem o label 'role=frontend'.
        A NetworkPolicy permite ingress de pods com label 'role=api'.
        Corrija o label no ingress from para 'role=frontend'.

Dica 3: kubectl edit networkpolicy backend-policy -n scenario-13
        Altere o ingress.from.podSelector.matchLabels de
          role: api
        para
          role: frontend

Dica 4: Teste:
        kubectl exec frontend -n scenario-13 -- wget -qO- --timeout=3 http://backend"""


def deploy() -> tuple:
    kubectl(["create", "namespace", NS])
    r = apply_yaml("""\
apiVersion: v1
kind: Pod
metadata:
  name: backend
  namespace: scenario-13
  labels:
    role: backend
spec:
  containers:
  - name: nginx
    image: nginx:1.25
    ports:
    - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: scenario-13
spec:
  selector:
    role: backend
  ports:
  - port: 80
---
apiVersion: v1
kind: Pod
metadata:
  name: frontend
  namespace: scenario-13
  labels:
    role: frontend
spec:
  containers:
  - name: client
    image: busybox:1.36
    command: ["sh", "-c", "sleep 3600"]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-policy
  namespace: scenario-13
spec:
  podSelector:
    matchLabels:
      role: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: api
    ports:
    - protocol: TCP
      port: 80
""")
    if r.returncode != 0:
        return False, r.stderr.strip()
    return True, "NetworkPolicy criada permitindo ingress de 'role=api' (mas frontend tem 'role=frontend')."


def verify() -> tuple:
    wait_for(lambda: _pods_ready(), timeout=60)

    r = exec_in_pod("frontend", NS, "wget -qO- --timeout=5 http://backend 2>/dev/null | head -1")
    if r.returncode == 0 and r.stdout.strip():
        r2 = kubectl(["get", "networkpolicy", "backend-policy", "-n", NS])
        if r2.returncode != 0:
            return False, "Conexão funcionando mas a NetworkPolicy foi removida — corrija-a sem deletar."
        return True, "Frontend consegue acessar o backend e a NetworkPolicy ainda existe."
    return False, "frontend ainda não consegue acessar o backend. Verifique a NetworkPolicy."


def _pods_ready() -> bool:
    for pod in ["frontend", "backend"]:
        r = kubectl(["get", "pod", pod, "-n", NS,
                     "-o", "jsonpath={.status.phase}"])
        if r.stdout.strip() != "Running":
            return False
    return True


def reset() -> tuple:
    delete_ns(NS)
    return True, f"Namespace {NS} removido."
