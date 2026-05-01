from scenarios.helpers import vssh, node_ready, wait_for, node_name

METADATA = {
    "id": "01-node-notready",
    "title": "Node NotReady",
    "category": "Troubleshooting",
    "lab_ref": "labs/05-troubleshooting.md",
    "difficulty": "intermediario",
}

DESCRIPTION = """\
╔══════════════════════════════════════════════════════════════════╗
║  CENÁRIO 01 — Node NotReady                                      ║
╠══════════════════════════════════════════════════════════════════╣
║  Um node do cluster está com status NotReady.                    ║
║                                                                  ║
║  TAREFA                                                          ║
║  Identifique por que o node cka-lab-wk-2 está NotReady           ║
║  e corrija o problema para que ele volte ao status Ready.        ║
║                                                                  ║
║  Dica: comece com kubectl get nodes e kubectl describe node.     ║
╚══════════════════════════════════════════════════════════════════╝"""

HINT = """\
Dica 1: Execute 'kubectl describe node cka-lab-wk-2' e leia a seção Conditions.

Dica 2: Acesse o node via SSH:
        ssh -i /home/vagrant/.ssh/lab_key vagrant@192.168.99.12

Dica 3: Dentro do node, verifique o kubelet:
        systemctl status kubelet
        journalctl -u kubelet -n 30

Dica 4: Se o kubelet estiver parado, habilite e inicie:
        sudo systemctl enable kubelet && sudo systemctl start kubelet"""


def deploy() -> tuple:
    r = vssh("wk-2", "sudo systemctl stop kubelet && sudo systemctl disable kubelet")
    if r.returncode != 0:
        return False, f"Falha ao parar kubelet em wk-2: {r.stderr.strip()}"
    return True, "kubelet de wk-2 foi parado e desabilitado. Node ficará NotReady em ~40s."


def verify() -> tuple:
    if node_ready("wk-2"):
        return True, f"Node {node_name('wk-2')} está Ready."
    return False, f"Node {node_name('wk-2')} ainda não está Ready."


def reset() -> tuple:
    vssh("wk-2", "sudo systemctl enable kubelet && sudo systemctl start kubelet")
    ok = wait_for(lambda: node_ready("wk-2"), timeout=90)
    if ok:
        return True, "kubelet de wk-2 restaurado. Node voltou ao estado Ready."
    return False, "kubelet iniciado mas node ainda não voltou a Ready. Aguarde mais alguns segundos."
