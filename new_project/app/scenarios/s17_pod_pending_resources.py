from scenarios.helpers import kubectl, apply_yaml, delete_ns

METADATA = {
    "id": "17-pod-pending-resources",
    "title": "Pod Pending por resource request excessivo",
    "category": "Workloads",
    "lab_ref": "labs/02-workloads-scheduling.md",
    "difficulty": "iniciante",
}

NS = "scenario-17"

DESCRIPTION = """\
╔══════════════════════════════════════════════════════════════════╗
║  CENÁRIO 17 — Pod Pending por resource request excessivo         ║
╠══════════════════════════════════════════════════════════════════╣
║  O pod 'heavy-worker' no namespace scenario-17 está Pending      ║
║  há vários minutos sem ser agendado em nenhum node.              ║
║                                                                  ║
║  TAREFA                                                          ║
║  Identifique por que o pod não é agendado e corrija-o para       ║
║  que fique Running. O pod deve fazer a mesma tarefa              ║
║  (processar dados com CPU) mas com requests adequados.           ║
║                                                                  ║
║  Namespace: scenario-17                                          ║
╚══════════════════════════════════════════════════════════════════╝"""

HINT = """\
Dica 1: kubectl describe pod heavy-worker -n scenario-17
        Leia a seção 'Events'. O que está impedindo o agendamento?

Dica 2: kubectl describe nodes | grep -A5 'Allocated resources'
        Quanto de CPU está disponível em cada node?

Dica 3: O pod solicita 8 CPUs mas nenhum node tem tanta capacidade.
        Exporte e corrija o requests.cpu:
        kubectl get pod heavy-worker -n scenario-17 -o yaml > /tmp/heavy.yaml
        # Reduza requests.cpu para 500m ou menos
        kubectl delete pod heavy-worker -n scenario-17
        kubectl apply -f /tmp/heavy.yaml"""


def deploy() -> tuple:
    kubectl(["create", "namespace", NS])
    r = apply_yaml("""\
apiVersion: v1
kind: Pod
metadata:
  name: heavy-worker
  namespace: scenario-17
spec:
  containers:
  - name: worker
    image: busybox:1.36
    command: ["sh", "-c", "echo Processing; sleep 3600"]
    resources:
      requests:
        cpu: "8"
        memory: "64Mi"
      limits:
        cpu: "8"
        memory: "128Mi"
""")
    if r.returncode != 0:
        return False, r.stderr.strip()
    return True, "Pod 'heavy-worker' criado com request de 8 CPUs — maior que qualquer node disponível."


def verify() -> tuple:
    r = kubectl(["get", "pod", "heavy-worker", "-n", NS,
                 "-o", "jsonpath={.status.phase}"])
    phase = r.stdout.strip()
    if phase == "Running":
        r2 = kubectl(["get", "pod", "heavy-worker", "-n", NS,
                      "-o", "jsonpath={.spec.containers[0].resources.requests.cpu}"])
        cpu = r2.stdout.strip()
        return True, f"Pod 'heavy-worker' Running com request de CPU: {cpu}."
    if phase == "Pending":
        r3 = kubectl(["get", "events", "-n", NS,
                      "--field-selector=involvedObject.name=heavy-worker",
                      "-o", "jsonpath={.items[-1].message}"])
        msg = r3.stdout.strip()[:80]
        return False, f"Pod ainda Pending. Evento: {msg or 'Insufficient cpu'}."
    return False, f"Pod em estado '{phase}'."


def reset() -> tuple:
    delete_ns(NS)
    return True, f"Namespace {NS} removido."
