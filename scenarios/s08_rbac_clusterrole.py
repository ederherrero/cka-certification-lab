from scenarios.helpers import kubectl, apply_yaml, can_i

METADATA = {
    "id": "08-rbac-clusterrole",
    "title": "ClusterRole — acesso somente leitura global",
    "category": "Architecture",
    "lab_ref": "labs/01-cluster-architecture.md",
    "difficulty": "intermediario",
}

SA = "monitor"
SA_NS = "monitoring"

DESCRIPTION = """\
╔══════════════════════════════════════════════════════════════════╗
║  CENÁRIO 08 — ClusterRole: acesso somente leitura global         ║
╠══════════════════════════════════════════════════════════════════╣
║  A equipe de operações usa o ServiceAccount 'monitor' no         ║
║  namespace 'monitoring' para observar o cluster.                 ║
║  Atualmente não tem nenhuma permissão.                           ║
║                                                                  ║
║  TAREFA                                                          ║
║  Configure o RBAC para que o ServiceAccount 'monitor' possa:     ║
║    • listar e obter Pods em TODOS os namespaces                  ║
║    • listar e obter Nodes (recurso de cluster)                   ║
║  Não deve ter permissão de criar ou deletar nada.                ║
║                                                                  ║
║  Namespace do ServiceAccount: monitoring                         ║
╚══════════════════════════════════════════════════════════════════╝"""

HINT = """\
Dica 1: Como o acesso é em TODOS os namespaces, você precisa de
        ClusterRole + ClusterRoleBinding (não Role + RoleBinding).

Dica 2: kubectl create clusterrole cluster-monitor \\
          --verb=get,list \\
          --resource=pods,nodes

Dica 3: kubectl create clusterrolebinding cluster-monitor-binding \\
          --clusterrole=cluster-monitor \\
          --serviceaccount=monitoring:monitor

Dica 4: Validar:
        kubectl auth can-i list pods --all-namespaces \\
          --as=system:serviceaccount:monitoring:monitor
        kubectl auth can-i list nodes \\
          --as=system:serviceaccount:monitoring:monitor"""


def deploy() -> tuple:
    kubectl(["create", "namespace", SA_NS])
    r = apply_yaml(f"""\
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {SA}
  namespace: {SA_NS}
""")
    if r.returncode != 0:
        return False, r.stderr.strip()
    return True, f"ServiceAccount '{SA}' criado em namespace '{SA_NS}' sem nenhuma permissão."


def verify() -> tuple:
    # Pode listar pods em default e kube-system
    ok_pods_default  = can_i("list", "pods", "default",     SA_NS, SA)
    ok_pods_system   = can_i("list", "pods", "kube-system", SA_NS, SA)
    ok_get_pods      = can_i("get",  "pods", "default",     SA_NS, SA)
    # Pode listar nodes (cluster-scoped — namespace é irrelevante, usa default)
    r_nodes = kubectl(["auth", "can-i", "list", "nodes",
                       f"--as=system:serviceaccount:{SA_NS}:{SA}"])
    ok_nodes = r_nodes.returncode == 0 and r_nodes.stdout.strip() == "yes"
    # Não pode deletar pods
    deny_delete = not can_i("delete", "pods", "default", SA_NS, SA)

    if ok_pods_default and ok_pods_system and ok_get_pods and ok_nodes and deny_delete:
        return True, f"ServiceAccount '{SA}' tem acesso de leitura em todos os namespaces e nodes, sem poder deletar."

    missing = []
    if not ok_pods_default:
        missing.append("listar pods em 'default'")
    if not ok_pods_system:
        missing.append("listar pods em 'kube-system'")
    if not ok_nodes:
        missing.append("listar nodes")
    if not deny_delete:
        missing.append("(ATENÇÃO: pode deletar pods — permissão excessiva)")
    return False, "Permissões faltando: " + ", ".join(missing)


def reset() -> tuple:
    kubectl(["delete", "clusterrolebinding", "cluster-monitor-binding", "--ignore-not-found"])
    kubectl(["delete", "clusterrole", "cluster-monitor", "--ignore-not-found"])
    kubectl(["delete", "namespace", SA_NS, "--ignore-not-found"])
    return True, f"ClusterRole, ClusterRoleBinding e namespace '{SA_NS}' removidos."
