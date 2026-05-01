from scenarios.helpers import kubectl, apply_yaml, delete_ns, endpoints_filled

METADATA = {
    "id": "12-svc-no-endpoints",
    "title": "Service sem endpoints",
    "category": "Networking",
    "lab_ref": "labs/03-services-networking.md",
    "difficulty": "intermediario",
}

NS = "scenario-12"

DESCRIPTION = """\
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
║                                                                  ║
║  Namespace: scenario-12                                          ║
╚══════════════════════════════════════════════════════════════════╝"""

HINT = """\
Dica 1: kubectl get endpoints web-svc -n scenario-12
        Se aparecer '<none>', o seletor do Service não bate com nenhum pod.

Dica 2: Compare o seletor do service com os labels dos pods:
        kubectl describe service web-svc -n scenario-12 | grep Selector
        kubectl get pods -n scenario-12 --show-labels

Dica 3: kubectl edit service web-svc -n scenario-12
        Corrija o campo spec.selector para bater com os labels dos pods.

Dica 4: Após corrigir, verifique:
        kubectl get endpoints web-svc -n scenario-12"""


def deploy() -> tuple:
    kubectl(["create", "namespace", NS])
    r = apply_yaml("""\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: scenario-12
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web
      tier: frontend
  template:
    metadata:
      labels:
        app: web
        tier: frontend
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
  name: web-svc
  namespace: scenario-12
spec:
  selector:
    app: webapp
  ports:
  - port: 80
    targetPort: 80
""")
    if r.returncode != 0:
        return False, r.stderr.strip()
    return True, "Deployment 'web' criado com selector 'app=web' mas Service usa 'app=webapp' (errado)."


def verify() -> tuple:
    if endpoints_filled("web-svc", NS):
        return True, "Service 'web-svc' tem endpoints. O seletor está correto."
    r = kubectl(["describe", "service", "web-svc", "-n", NS])
    sel_line = [l for l in r.stdout.splitlines() if "Selector" in l]
    sel = sel_line[0].strip() if sel_line else "desconhecido"
    return False, f"Service ainda sem endpoints. Seletor atual: {sel}"


def reset() -> tuple:
    delete_ns(NS)
    return True, f"Namespace {NS} removido."
