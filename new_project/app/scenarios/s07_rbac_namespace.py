from scenarios.helpers import kubectl, apply_yaml, delete_ns, can_i

METADATA = {
    "id": "07-rbac-namespace",
    "title": "RBAC — ServiceAccount sem permissão",
    "category": "Architecture",
    "lab_ref": "labs/01-cluster-architecture.md",
    "difficulty": "intermediario",
}

NS = "scenario-07"

DESCRIPTION = """\
╔══════════════════════════════════════════════════════════════════╗
║  CENÁRIO 07 — RBAC: ServiceAccount sem permissão                 ║
╠══════════════════════════════════════════════════════════════════╣
║  A aplicação 'pod-inspector' usa o ServiceAccount 'app-sa'       ║
║  no namespace scenario-07 para listar pods. Os logs mostram      ║
║  '403 Forbidden' ao chamar a API do Kubernetes.                  ║
║                                                                  ║
║  TAREFA                                                          ║
║  Crie as permissões RBAC necessárias para que o ServiceAccount   ║
║  'app-sa' possa listar e obter pods no namespace scenario-07.    ║
║  O ServiceAccount não deve ter permissões em outros namespaces.  ║
║                                                                  ║
║  Namespace: scenario-07                                          ║
╚══════════════════════════════════════════════════════════════════╝"""

HINT = """\
Dica 1: Você precisa de 3 recursos: Role, ServiceAccount e RoleBinding.
        O ServiceAccount já existe. Crie a Role e o RoleBinding.

Dica 2: kubectl create role pod-reader \\
          --verb=get,list \\
          --resource=pods \\
          --namespace=scenario-07

Dica 3: kubectl create rolebinding pod-reader-binding \\
          --role=pod-reader \\
          --serviceaccount=scenario-07:app-sa \\
          --namespace=scenario-07

Dica 4: Validar:
        kubectl auth can-i list pods -n scenario-07 \\
          --as=system:serviceaccount:scenario-07:app-sa"""


def deploy() -> tuple:
    kubectl(["create", "namespace", NS])
    r = apply_yaml("""\
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
  namespace: scenario-07
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pod-inspector
  namespace: scenario-07
spec:
  replicas: 1
  selector:
    matchLabels:
      app: pod-inspector
  template:
    metadata:
      labels:
        app: pod-inspector
    spec:
      serviceAccountName: app-sa
      containers:
      - name: inspector
        image: bitnami/kubectl:latest
        command: ["sh", "-c", "while true; do kubectl get pods -n scenario-07; sleep 10; done"]
""")
    if r.returncode != 0:
        return False, r.stderr.strip()
    return True, "ServiceAccount 'app-sa' criado sem nenhuma permissão em scenario-07."


def verify() -> tuple:
    ok_list = can_i("list", "pods", NS, NS, "app-sa")
    ok_get  = can_i("get",  "pods", NS, NS, "app-sa")
    deny_default = not can_i("list", "pods", "default", NS, "app-sa")

    if ok_list and ok_get and deny_default:
        return True, "ServiceAccount 'app-sa' pode listar/obter pods em scenario-07 e não tem acesso a outros namespaces."
    if not ok_list:
        return False, "app-sa ainda não pode listar pods em scenario-07."
    if not ok_get:
        return False, "app-sa pode listar mas não consegue 'get' em pods de scenario-07."
    if not deny_default:
        return False, "app-sa tem acesso ao namespace 'default' — use Role (não ClusterRole) para restringir ao namespace."
    return False, "Permissões incompletas."


def reset() -> tuple:
    kubectl(["delete", "rolebinding", "pod-reader-binding", "-n", NS, "--ignore-not-found"])
    kubectl(["delete", "role", "pod-reader", "-n", NS, "--ignore-not-found"])
    delete_ns(NS)
    return True, f"Namespace {NS} e recursos RBAC removidos."
