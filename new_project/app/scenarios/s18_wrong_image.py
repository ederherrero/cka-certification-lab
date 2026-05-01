from scenarios.helpers import kubectl, apply_yaml, delete_ns, deployment_ready

METADATA = {
    "id": "18-wrong-image",
    "title": "Deployment com imagem inexistente",
    "category": "Workloads",
    "lab_ref": "labs/02-workloads-scheduling.md",
    "difficulty": "iniciante",
}

NS = "scenario-18"

DESCRIPTION = """\
╔══════════════════════════════════════════════════════════════════╗
║  CENÁRIO 18 — Deployment com imagem inexistente                  ║
╠══════════════════════════════════════════════════════════════════╣
║  O Deployment 'api-server' no namespace scenario-18 foi          ║
║  atualizado por um pipeline de CI/CD mas os pods estão em        ║
║  ErrImagePull / ImagePullBackOff.                                ║
║                                                                  ║
║  TAREFA                                                          ║
║  Corrija o Deployment 'api-server' para usar uma imagem válida.  ║
║  Use nginx:1.25 como imagem de substituição.                     ║
║                                                                  ║
║  Namespace: scenario-18                                          ║
╚══════════════════════════════════════════════════════════════════╝"""

HINT = """\
Dica 1: kubectl describe pod -n scenario-18 | grep -A3 'Events'
        Qual imagem está tentando usar?

Dica 2: kubectl get deployment api-server -n scenario-18 -o yaml | grep image

Dica 3: Corrija a imagem diretamente:
        kubectl set image deployment/api-server \\
          api-server=nginx:1.25 \\
          -n scenario-18

Dica 4: Acompanhe o rollout:
        kubectl rollout status deployment api-server -n scenario-18"""


def deploy() -> tuple:
    kubectl(["create", "namespace", NS])
    r = apply_yaml("""\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
  namespace: scenario-18
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api-server
  template:
    metadata:
      labels:
        app: api-server
    spec:
      containers:
      - name: api-server
        image: nginx:THIS-TAG-DOES-NOT-EXIST
        ports:
        - containerPort: 80
""")
    if r.returncode != 0:
        return False, r.stderr.strip()
    return True, "Deployment 'api-server' criado com imagem inválida 'nginx:THIS-TAG-DOES-NOT-EXIST'."


def verify() -> tuple:
    if deployment_ready("api-server", NS):
        r = kubectl(["get", "deployment", "api-server", "-n", NS,
                     "-o", "jsonpath={.spec.template.spec.containers[0].image}"])
        img = r.stdout.strip()
        return True, f"Deployment 'api-server' disponível com imagem: {img}."

    r2 = kubectl(["get", "pods", "-n", NS,
                  "-o", "jsonpath={.items[0].status.containerStatuses[0].state.waiting.reason}"])
    reason = r2.stdout.strip()
    if reason in ("ErrImagePull", "ImagePullBackOff"):
        r3 = kubectl(["get", "deployment", "api-server", "-n", NS,
                      "-o", "jsonpath={.spec.template.spec.containers[0].image}"])
        img = r3.stdout.strip()
        return False, f"Ainda com erro de imagem ({reason}). Imagem atual: {img}."
    return False, f"Deployment ainda não disponível. Estado: {reason or 'aguardando'}."


def reset() -> tuple:
    delete_ns(NS)
    return True, f"Namespace {NS} removido."
