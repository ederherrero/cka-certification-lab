from scenarios.helpers import kubectl, vssh, wait_for

METADATA = {
    "id": "11-static-pod",
    "title": "Criar um static pod no control plane",
    "category": "Architecture",
    "lab_ref": "labs/01-cluster-architecture.md",
    "difficulty": "intermediario",
}

POD_NAME = "monitor-cp-1"
MANIFEST_DEST = "/etc/kubernetes/manifests/monitor.yaml"

DESCRIPTION = """\
╔══════════════════════════════════════════════════════════════════╗
║  CENÁRIO 11 — Criar um static pod no control plane               ║
╠══════════════════════════════════════════════════════════════════╣
║  A equipe precisa de um pod de monitoramento rodando diretamente ║
║  no control plane como um static pod.                            ║
║                                                                  ║
║  TAREFA                                                          ║
║  Crie um static pod chamado 'monitor' no control plane (cp-1)    ║
║  com as seguintes especificações:                                ║
║    • imagem: busybox:1.36                                        ║
║    • comando: sh -c "while true; do date; sleep 30; done"        ║
║    • o pod deve aparecer como 'monitor-cp-1' em kube-system      ║
║                                                                  ║
║  Acesso: cd vagrant && vagrant ssh cp-1                          ║
╚══════════════════════════════════════════════════════════════════╝"""

HINT = """\
Dica 1: Static pods são gerenciados pelo kubelet, não pelo API server.
        Seus manifests ficam em /etc/kubernetes/manifests/ no node.

Dica 2: Crie o arquivo no cp-1:
        sudo tee /etc/kubernetes/manifests/monitor.yaml << 'EOF'
        apiVersion: v1
        kind: Pod
        metadata:
          name: monitor
          namespace: kube-system
        spec:
          containers:
          - name: monitor
            image: busybox:1.36
            command: ["sh", "-c", "while true; do date; sleep 30; done"]
        EOF

Dica 3: O kubelet detecta o arquivo automaticamente e cria o pod.
        O nome do pod será 'monitor-cp-1' (nome + sufixo do node).
        Verifique: kubectl get pod monitor-cp-1 -n kube-system"""


def deploy() -> tuple:
    # Remover o manifest caso já exista (para forçar o cenário)
    vssh("cp-1", f"sudo rm -f {MANIFEST_DEST}")

    # Aguardar o pod sumir caso exista
    import time
    time.sleep(5)

    return True, "Manifest do static pod removido. Crie /etc/kubernetes/manifests/monitor.yaml no cp-1."


def verify() -> tuple:
    r = kubectl(["get", "pod", POD_NAME, "-n", "kube-system",
                 "-o", "jsonpath={.status.phase}"])
    phase = r.stdout.strip()
    if phase == "Running":
        return True, f"Static pod '{POD_NAME}' está Running em kube-system."
    if phase:
        return False, f"Pod '{POD_NAME}' existe mas está em fase '{phase}'."
    return False, f"Pod '{POD_NAME}' não encontrado em kube-system. Verifique se o manifest está em {MANIFEST_DEST} no cp-1."


def reset() -> tuple:
    vssh("cp-1", f"sudo rm -f {MANIFEST_DEST}")
    import time
    time.sleep(5)
    return True, f"Manifest do static pod removido de {MANIFEST_DEST}."
