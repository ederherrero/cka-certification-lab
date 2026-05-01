from scenarios.helpers import kubectl, apply_yaml, delete_ns, node_name

METADATA = {
    "id": "16-pod-pending-taint",
    "title": "Pod Pending por taint sem toleration",
    "category": "Workloads",
    "lab_ref": "labs/02-workloads-scheduling.md",
    "difficulty": "intermediario",
}

NS = "scenario-16"
NODE = "wk-3"

DESCRIPTION = """\
╔══════════════════════════════════════════════════════════════════╗
║  CENÁRIO 16 — Pod Pending por taint sem toleration               ║
╠══════════════════════════════════════════════════════════════════╣
║  O pod 'gpu-worker' no namespace scenario-16 está Pending.       ║
║  Ele deve rodar especificamente no node wk-3 mas não consegue    ║
║  ser agendado lá.                                                ║
║                                                                  ║
║  TAREFA                                                          ║
║  Corrija o pod 'gpu-worker' para que ele rode no node            ║
║  cka-lab-wk-3.                                                   ║
║                                                                  ║
║  Restrição: o pod deve ter um nodeSelector ou nodeName           ║
║  apontando para wk-3.                                            ║
║                                                                  ║
║  Namespace: scenario-16                                          ║
╚══════════════════════════════════════════════════════════════════╝"""

HINT = """\
Dica 1: kubectl describe pod gpu-worker -n scenario-16
        Leia a seção 'Events' — qual taint está bloqueando?

Dica 2: kubectl describe node cka-lab-wk-3 | grep Taint

Dica 3: O pod precisa de uma toleration para o taint 'env=prod:NoSchedule'.
        Exporte, corrija e recrie o pod:
        kubectl get pod gpu-worker -n scenario-16 -o yaml > /tmp/gpu.yaml
        # Adicione em spec.tolerations:
        # - key: env
        #   operator: Equal
        #   value: prod
        #   effect: NoSchedule
        kubectl delete pod gpu-worker -n scenario-16
        kubectl apply -f /tmp/gpu.yaml"""


def deploy() -> tuple:
    full_node = node_name(NODE)
    kubectl(["taint", "node", full_node, "env=prod:NoSchedule", "--overwrite"])
    kubectl(["create", "namespace", NS])

    r = apply_yaml(f"""\
apiVersion: v1
kind: Pod
metadata:
  name: gpu-worker
  namespace: scenario-16
spec:
  nodeName: {full_node}
  containers:
  - name: worker
    image: busybox:1.36
    command: ["sh", "-c", "echo GPU task; sleep 3600"]
    resources:
      requests:
        cpu: "100m"
        memory: "64Mi"
""")
    if r.returncode != 0:
        return False, r.stderr.strip()
    return True, f"Taint 'env=prod:NoSchedule' aplicado em {full_node}. Pod 'gpu-worker' sem toleration ficará Pending."


def verify() -> tuple:
    r = kubectl(["get", "pod", "gpu-worker", "-n", NS,
                 "-o", "jsonpath={.status.phase},{.spec.nodeName}"])
    parts = r.stdout.strip().split(",")
    phase = parts[0] if parts else ""
    node = parts[1] if len(parts) > 1 else ""
    full = node_name(NODE)

    if phase == "Running" and full in node:
        return True, f"Pod 'gpu-worker' está Running em {full}."
    if phase == "Running":
        return False, f"Pod Running mas em '{node}' — deveria estar em {full}."
    return False, f"Pod ainda não está Running. Fase: {phase or 'Pending'}."


def reset() -> tuple:
    full_node = node_name(NODE)
    kubectl(["taint", "node", full_node, "env=prod:NoSchedule-"])
    delete_ns(NS)
    return True, f"Taint removido de {full_node} e namespace {NS} removido."
