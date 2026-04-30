from scenarios.helpers import kubectl, apply_yaml, delete_ns, deployment_ready, wait_for

METADATA = {
    "id": "02-pod-crashloop",
    "title": "Pod em CrashLoopBackOff",
    "category": "Troubleshooting",
    "lab_ref": "labs/05-troubleshooting.md",
    "difficulty": "iniciante",
}

NS = "scenario-02"

DESCRIPTION = """\
╔══════════════════════════════════════════════════════════════════╗
║  CENÁRIO 02 — Pod em CrashLoopBackOff                            ║
╠══════════════════════════════════════════════════════════════════╣
║  Um Deployment no namespace scenario-02 está falhando.           ║
║  Os pods entram em CrashLoopBackOff logo após iniciarem.         ║
║                                                                  ║
║  TAREFA                                                          ║
║  Corrija o Deployment 'webapp' no namespace scenario-02 para     ║
║  que seus pods fiquem em status Running de forma estável.        ║
║                                                                  ║
║  Namespace: scenario-02                                          ║
╚══════════════════════════════════════════════════════════════════╝"""

HINT = """\
Dica 1: kubectl get pods -n scenario-02
        kubectl describe pod <nome> -n scenario-02
        Observe o campo 'Exit Code' e a seção 'Command'.

Dica 2: kubectl logs <pod> -n scenario-02 --previous
        Veja o que o container imprime antes de sair.

Dica 3: kubectl edit deployment webapp -n scenario-02
        Corrija o campo spec.template.spec.containers[0].command."""


def deploy() -> tuple:
    kubectl(["create", "namespace", NS, "--dry-run=client", "-o", "yaml"])
    kubectl(["create", "namespace", NS])
    manifest = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webapp
  namespace: scenario-02
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
      - name: webapp
        image: nginx:1.25
        command: ["sh", "-c", "echo Iniciando; exit 1"]
"""
    r = apply_yaml(manifest)
    if r.returncode != 0:
        return False, r.stderr.strip()
    return True, "Deployment 'webapp' criado com comando inválido em scenario-02."


def verify() -> tuple:
    r = deployment_ready("webapp", NS)
    if r:
        return True, "Deployment 'webapp' está disponível com todos os pods Running."
    pod_r = kubectl(["get", "pods", "-n", NS,
                     "-o", "jsonpath={.items[0].status.containerStatuses[0].state.waiting.reason}"])
    reason = pod_r.stdout.strip()
    return False, f"Pods ainda não estão Running. Estado atual: {reason or 'desconhecido'}."


def reset() -> tuple:
    delete_ns(NS)
    return True, f"Namespace {NS} removido."
