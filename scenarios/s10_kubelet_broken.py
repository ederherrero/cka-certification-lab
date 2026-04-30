from scenarios.helpers import vssh, node_ready, wait_for

METADATA = {
    "id": "10-kubelet-broken",
    "title": "Kubelet com configuração errada",
    "category": "Architecture",
    "lab_ref": "labs/01-cluster-architecture.md",
    "difficulty": "avancado",
}

NODE = "wk-1"
KUBELET_CONFIG = "/var/lib/kubelet/config.yaml"
BACKUP_CONFIG = "/tmp/kubelet-config-backup.yaml"
WRONG_DNS = "10.96.0.99"
CORRECT_DNS = "10.96.0.10"

DESCRIPTION = """\
╔══════════════════════════════════════════════════════════════════╗
║  CENÁRIO 10 — Kubelet com configuração errada                    ║
╠══════════════════════════════════════════════════════════════════╣
║  O node wk-1 está com status NotReady após uma manutenção.       ║
║  A equipe suspeita que a configuração do kubelet foi alterada.   ║
║                                                                  ║
║  TAREFA                                                          ║
║  Identifique e corrija a configuração errada do kubelet no       ║
║  node cka-certification-lab-wk-1 para que ele volte a Ready.    ║
║                                                                  ║
║  Acesso: cd vagrant && vagrant ssh wk-1                          ║
╚══════════════════════════════════════════════════════════════════╝"""

HINT = """\
Dica 1: Acesse o node: cd vagrant && vagrant ssh wk-1

Dica 2: Verifique o log do kubelet para ver o erro específico:
        sudo journalctl -u kubelet -n 50 --no-pager

Dica 3: A configuração principal do kubelet fica em:
        /var/lib/kubelet/config.yaml
        Procure pelo campo clusterDNS.

Dica 4: O IP correto do kube-dns é o primeiro IP do service CIDR.
        Para service_cidr 10.96.0.0/12, o DNS fica em 10.96.0.10.
        sudo sed -i 's/10.96.0.99/10.96.0.10/' /var/lib/kubelet/config.yaml
        sudo systemctl restart kubelet"""


def deploy() -> tuple:
    # Fazer backup e alterar o clusterDNS para um IP errado
    r = vssh(NODE, (
        f"sudo cp {KUBELET_CONFIG} {BACKUP_CONFIG} && "
        f"sudo sed -i 's/{CORRECT_DNS}/{WRONG_DNS}/g' {KUBELET_CONFIG} && "
        f"sudo systemctl restart kubelet"
    ))
    if r.returncode != 0:
        return False, f"Falha ao alterar configuração: {r.stderr.strip()}"
    return True, f"clusterDNS do kubelet em {NODE} alterado para {WRONG_DNS}. Node ficará NotReady."


def verify() -> tuple:
    # Verificar se o clusterDNS está correto
    r = vssh(NODE, f"sudo grep 'clusterDNS' {KUBELET_CONFIG}")
    if WRONG_DNS in r.stdout:
        return False, f"kubelet ainda usa DNS errado ({WRONG_DNS}). Corrija e reinicie o kubelet."

    if not node_ready(NODE):
        return False, f"Configuração pode estar correta mas node {NODE} ainda não está Ready."

    return True, f"clusterDNS corrigido e node {NODE} está Ready."


def reset() -> tuple:
    vssh(NODE, (
        f"sudo cp {BACKUP_CONFIG} {KUBELET_CONFIG} 2>/dev/null || "
        f"sudo sed -i 's/{WRONG_DNS}/{CORRECT_DNS}/g' {KUBELET_CONFIG}; "
        f"sudo systemctl restart kubelet"
    ))
    wait_for(lambda: node_ready(NODE), timeout=90)
    return True, f"Configuração do kubelet em {NODE} restaurada."
