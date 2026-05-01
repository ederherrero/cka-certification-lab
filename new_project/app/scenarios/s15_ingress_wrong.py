from scenarios.helpers import kubectl, apply_yaml, delete_ns

METADATA = {
    "id": "15-ingress-wrong",
    "title": "Ingress com backend incorreto",
    "category": "Networking",
    "lab_ref": "labs/03-services-networking.md",
    "difficulty": "avancado",
}

NS = "scenario-15"

DESCRIPTION = """\
╔══════════════════════════════════════════════════════════════════╗
║  CENÁRIO 15 — Ingress com backend incorreto                      ║
╠══════════════════════════════════════════════════════════════════╣
║  O Ingress 'app-ingress' no namespace scenario-15 está           ║
║  configurado mas retorna 503 (service unavailable).              ║
║  O Deployment e o Service da aplicação estão Running.            ║
║                                                                  ║
║  TAREFA                                                          ║
║  Corrija o Ingress 'app-ingress' para que ele roteie             ║
║  requisições ao path '/' para o service correto da aplicação.    ║
║                                                                  ║
║  Namespace: scenario-15                                          ║
╚══════════════════════════════════════════════════════════════════╝"""

HINT = """\
Dica 1: kubectl describe ingress app-ingress -n scenario-15
        Leia o campo 'Rules' — qual service o backend aponta?

Dica 2: kubectl get services -n scenario-15
        Qual é o nome real do service disponível?

Dica 3: kubectl edit ingress app-ingress -n scenario-15
        Corrija spec.rules[0].http.paths[0].backend.service.name
        para o nome correto do service.

Dica 4: O service correto é 'webapp-svc' (não 'app-service')."""


def deploy() -> tuple:
    kubectl(["create", "namespace", NS])

    r = apply_yaml("""\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webapp
  namespace: scenario-15
spec:
  replicas: 2
  selector:
    matchLabels:
      app: webapp
  template:
    metadata:
      labels:
        app: webapp
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
  name: webapp-svc
  namespace: scenario-15
spec:
  selector:
    app: webapp
  ports:
  - port: 80
    targetPort: 80
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  namespace: scenario-15
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: app-service
            port:
              number: 80
""")
    if r.returncode != 0:
        return False, r.stderr.strip()
    return True, "Ingress criado com backend 'app-service' (errado). Service correto é 'webapp-svc'."


def verify() -> tuple:
    r = kubectl(["get", "ingress", "app-ingress", "-n", NS,
                 "-o", "jsonpath={.spec.rules[0].http.paths[0].backend.service.name}"])
    svc_name = r.stdout.strip()
    if svc_name != "webapp-svc":
        return False, f"Ingress ainda aponta para '{svc_name}'. Deve apontar para 'webapp-svc'."

    r2 = kubectl(["get", "endpoints", "webapp-svc", "-n", NS,
                  "-o", "jsonpath={.subsets[0].addresses[0].ip}"])
    if not r2.stdout.strip():
        return False, "Ingress correto mas service 'webapp-svc' sem endpoints."

    return True, "Ingress 'app-ingress' corrigido — backend aponta para 'webapp-svc' com endpoints válidos."


def reset() -> tuple:
    delete_ns(NS)
    return True, f"Namespace {NS} removido."
