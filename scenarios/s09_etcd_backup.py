from scenarios.helpers import vssh

METADATA = {
    "id": "09-etcd-backup",
    "title": "Backup do etcd",
    "category": "Architecture",
    "lab_ref": "labs/01-cluster-architecture.md",
    "difficulty": "intermediario",
}

SNAPSHOT_PATH = "/tmp/etcd-snapshot.db"

DESCRIPTION = """\
╔══════════════════════════════════════════════════════════════════╗
║  CENÁRIO 09 — Backup do etcd                                     ║
╠══════════════════════════════════════════════════════════════════╣
║  O procedimento de backup do etcd não foi executado hoje.        ║
║                                                                  ║
║  TAREFA                                                          ║
║  Crie um snapshot do etcd em:                                    ║
║    /tmp/etcd-snapshot.db                                         ║
║  no control plane (cp-1).                                        ║
║                                                                  ║
║  O snapshot deve ser válido (verificável com etcdctl).           ║
║                                                                  ║
║  Acesso: cd vagrant && vagrant ssh cp-1                          ║
╚══════════════════════════════════════════════════════════════════╝"""

HINT = """\
Dica 1: Acesse o control plane:
        cd vagrant && vagrant ssh cp-1

Dica 2: Verifique os certificados usados pelo etcd:
        sudo cat /etc/kubernetes/manifests/etcd.yaml | grep -E 'cert|key|trusted|listen'

Dica 3: Comando para criar o backup:
        sudo ETCDCTL_API=3 etcdctl snapshot save /tmp/etcd-snapshot.db \\
          --endpoints=https://127.0.0.1:2379 \\
          --cacert=/etc/kubernetes/pki/etcd/ca.crt \\
          --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \\
          --key=/etc/kubernetes/pki/etcd/healthcheck-client.key

Dica 4: Verificar o backup:
        sudo ETCDCTL_API=3 etcdctl snapshot status /tmp/etcd-snapshot.db --write-out=table"""


def deploy() -> tuple:
    # Remover backup anterior se existir
    vssh("cp-1", f"sudo rm -f {SNAPSHOT_PATH}")
    return True, f"Qualquer snapshot anterior em {SNAPSHOT_PATH} foi removido. Execute o backup no cp-1."


def verify() -> tuple:
    # Verificar se o arquivo existe
    r_exists = vssh("cp-1", f"test -f {SNAPSHOT_PATH} && echo exists")
    if "exists" not in r_exists.stdout:
        return False, f"Arquivo {SNAPSHOT_PATH} não encontrado no cp-1."

    # Verificar se é um snapshot válido
    r_status = vssh(
        "cp-1",
        f"sudo ETCDCTL_API=3 etcdctl snapshot status {SNAPSHOT_PATH} "
        f"--cacert=/etc/kubernetes/pki/etcd/ca.crt "
        f"--cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt "
        f"--key=/etc/kubernetes/pki/etcd/healthcheck-client.key "
        f"2>/dev/null && echo VALID"
    )
    if "VALID" not in r_status.stdout:
        # Tentar sem certs (etcdctl >= 3.5 pode verificar sem conectar ao servidor)
        r2 = vssh("cp-1", f"sudo ETCDCTL_API=3 etcdctl snapshot status {SNAPSHOT_PATH} 2>/dev/null && echo VALID")
        if "VALID" not in r2.stdout:
            return False, f"Arquivo existe em {SNAPSHOT_PATH} mas não é um snapshot válido."

    # Verificar tamanho mínimo (> 10KB indica snapshot real)
    r_size = vssh("cp-1", f"stat -c%s {SNAPSHOT_PATH} 2>/dev/null || echo 0")
    size = int(r_size.stdout.strip() or "0")
    if size < 10240:
        return False, f"Snapshot muito pequeno ({size} bytes). Pode estar corrompido ou vazio."

    return True, f"Snapshot válido encontrado em {SNAPSHOT_PATH} no cp-1 ({size // 1024} KB)."


def reset() -> tuple:
    vssh("cp-1", f"sudo rm -f {SNAPSHOT_PATH}")
    return True, f"Snapshot {SNAPSHOT_PATH} removido do cp-1."
