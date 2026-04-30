from scenarios.helpers import kubectl, vssh, apply_yaml, delete_ns, wait_for

METADATA = {
    "id": "05-scheduler-down",
    "title": "kube-scheduler fora do ar",
    "category": "Troubleshooting",
    "lab_ref": "labs/05-troubleshooting.md",
    "difficulty": "avancado",
}

NS = "scenario-05"
MANIFEST_PATH = "/etc/kubernetes/manifests/kube-scheduler.yaml"
BACKUP_PATH = "/tmp/kube-scheduler-backup.yaml"

DESCRIPTION = """\
╔══════════════════════════════════════════════════════════════════╗
║  CENÁRIO 05 — kube-scheduler fora do ar                          ║
╠══════════════════════════════════════════════════════════════════╣
║  Novos pods no cluster estão ficando presos em status Pending    ║
║  indefinidamente, mesmo com nodes disponíveis.                   ║
║                                                                  ║
║  TAREFA                                                          ║
║  Identifique o componente com problema e restaure o              ║
║  funcionamento normal do agendamento de pods.                    ║
║  Valide criando o pod de teste no namespace scenario-05.         ║
║                                                                  ║
║  Namespace: scenario-05                                          ║
╚══════════════════════════════════════════════════════════════════╝"""

HINT = """\
Dica 1: kubectl get pods -n kube-system
        Algum componente do control plane está ausente ou em erro?

Dica 2: Os componentes do control plane rodam como static pods.
        Seus manifests ficam em /etc/kubernetes/manifests/ no cp-1.

Dica 3: Acesse o control plane:
        cd vagrant && vagrant ssh cp-1
        ls /etc/kubernetes/manifests/
        O que está faltando?

Dica 4: Restaure o manifest do scheduler de /tmp/ para
        /etc/kubernetes/manifests/ — o kubelet recria o pod automaticamente."""


def deploy() -> tuple:
    # Fazer backup e remover o manifest do scheduler
    r = vssh("cp-1", f"sudo cp {MANIFEST_PATH} {BACKUP_PATH} && sudo rm {MANIFEST_PATH}")
    if r.returncode != 0:
        return False, f"Falha ao remover scheduler: {r.stderr.strip()}"

    # Criar namespace e pod de teste que ficará Pending
    kubectl(["create", "namespace", NS])
    pod = """\
apiVersion: v1
kind: Pod
metadata:
  name: test-pod
  namespace: scenario-05
spec:
  containers:
  - name: nginx
    image: nginx:1.25
"""
    apply_yaml(pod)
    return True, "kube-scheduler removido. Pod 'test-pod' em scenario-05 ficará Pending."


def verify() -> tuple:
    # Verificar se o scheduler está rodando
    r = kubectl(["get", "pod", "-n", "kube-system",
                 "-l", "component=kube-scheduler",
                 "-o", "jsonpath={.items[0].status.phase}"])
    if r.stdout.strip() != "Running":
        return False, "kube-scheduler ainda não está Running em kube-system."

    # Verificar se o pod de teste foi agendado
    r2 = kubectl(["get", "pod", "test-pod", "-n", NS,
                  "-o", "jsonpath={.status.phase}"])
    phase = r2.stdout.strip()
    if phase == "Running":
        return True, "kube-scheduler está Running e pod 'test-pod' foi agendado com sucesso."
    return False, f"kube-scheduler parece restaurado mas pod 'test-pod' ainda está {phase or 'Pending'}."


def reset() -> tuple:
    # Restaurar o manifest do scheduler
    vssh("cp-1", f"sudo cp {BACKUP_PATH} {MANIFEST_PATH} 2>/dev/null || true")
    delete_ns(NS)

    ok = wait_for(lambda: _scheduler_running(), timeout=60)
    if ok:
        return True, "kube-scheduler restaurado e namespace scenario-05 removido."
    return True, "Manifest restaurado. Aguarde o kubelet recriar o pod do scheduler (~30s)."


def _scheduler_running() -> bool:
    r = kubectl(["get", "pod", "-n", "kube-system",
                 "-l", "component=kube-scheduler",
                 "-o", "jsonpath={.items[0].status.phase}"])
    return r.stdout.strip() == "Running"
