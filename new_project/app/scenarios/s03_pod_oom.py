from scenarios.helpers import kubectl, apply_yaml, delete_ns, wait_for

METADATA = {
    "id": "03-pod-oom",
    "title": "Pod sendo OOMKilled",
    "category": "Troubleshooting",
    "lab_ref": "labs/05-troubleshooting.md",
    "difficulty": "iniciante",
}

NS = "scenario-03"

DESCRIPTION = """\
╔══════════════════════════════════════════════════════════════════╗
║  CENÁRIO 03 — Pod sendo OOMKilled                                ║
╠══════════════════════════════════════════════════════════════════╣
║  O pod 'memapp' no namespace scenario-03 é reiniciado            ║
║  continuamente com o motivo OOMKilled.                           ║
║                                                                  ║
║  TAREFA                                                          ║
║  Ajuste o memory limit do pod para que ele rode de forma estável.║
║  O processo dentro do container precisa de pelo menos 100Mi.     ║
║                                                                  ║
║  Namespace: scenario-03                                          ║
╚══════════════════════════════════════════════════════════════════╝"""

HINT = """\
Dica 1: kubectl describe pod memapp -n scenario-03
        Procure por 'OOMKilled' e 'Last State'.
        Observe o memory limit configurado.

Dica 2: Pods não podem ser editados diretamente enquanto rodam.
        Exporte o spec, corrija e recrie:
        kubectl get pod memapp -n scenario-03 -o yaml > /tmp/memapp.yaml
        # edite o limits.memory
        kubectl delete pod memapp -n scenario-03
        kubectl apply -f /tmp/memapp.yaml

Dica 3: O limite precisa ser >= 100Mi para o processo funcionar."""


def deploy() -> tuple:
    kubectl(["create", "namespace", NS])
    manifest = """\
apiVersion: v1
kind: Pod
metadata:
  name: memapp
  namespace: scenario-03
spec:
  containers:
  - name: memapp
    image: polinux/stress
    command: ["stress", "--vm", "1", "--vm-bytes", "90M", "--vm-hang", "1"]
    resources:
      requests:
        memory: "50Mi"
      limits:
        memory: "30Mi"
"""
    r = apply_yaml(manifest)
    if r.returncode != 0:
        return False, r.stderr.strip()
    return True, "Pod 'memapp' criado com memory limit insuficiente (30Mi para processo que precisa de 90Mi)."


def verify() -> tuple:
    r = kubectl(["get", "pod", "memapp", "-n", NS,
                 "-o", "jsonpath={.status.phase}"])
    phase = r.stdout.strip()
    if phase != "Running":
        r2 = kubectl(["get", "pod", "memapp", "-n", NS,
                      "-o", "jsonpath={.status.containerStatuses[0].state.waiting.reason}"])
        reason = r2.stdout.strip() or phase
        return False, f"Pod ainda não está Running. Estado: {reason}"

    r3 = kubectl(["get", "pod", "memapp", "-n", NS,
                  "-o", "jsonpath={.status.containerStatuses[0].restartCount}"])
    restarts = r3.stdout.strip()
    if restarts and int(restarts) > 2:
        return False, f"Pod está Running mas com {restarts} reinícios — ainda está sendo OOMKilled."

    return True, "Pod 'memapp' está Running de forma estável."


def reset() -> tuple:
    delete_ns(NS)
    return True, f"Namespace {NS} removido."
