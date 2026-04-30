from scenarios.helpers import kubectl, apply_yaml, delete_ns, pvc_bound

METADATA = {
    "id": "19-pvc-pending",
    "title": "PVC preso em Pending",
    "category": "Storage",
    "lab_ref": "labs/04-storage.md",
    "difficulty": "intermediario",
}

NS = "scenario-19"

DESCRIPTION = """\
╔══════════════════════════════════════════════════════════════════╗
║  CENÁRIO 19 — PVC preso em Pending                               ║
╠══════════════════════════════════════════════════════════════════╣
║  O pod 'db' no namespace scenario-19 está preso em              ║
║  ContainerCreating porque seu PVC não consegue fazer bind.       ║
║                                                                  ║
║  TAREFA                                                          ║
║  Corrija o problema para que o PVC 'db-storage' faça bind com    ║
║  um PV disponível e o pod 'db' fique Running.                    ║
║  Você pode criar um novo PV ou ajustar o PVC existente.          ║
║                                                                  ║
║  Namespace: scenario-19                                          ║
╚══════════════════════════════════════════════════════════════════╝"""

HINT = """\
Dica 1: kubectl describe pvc db-storage -n scenario-19
        Por que o PVC não faz bind? Veja a seção 'Events'.

Dica 2: kubectl get pv
        Existe algum PV disponível? Quais são seus accessModes?

Dica 3: O PVC solicita ReadWriteMany mas o PV disponível é ReadWriteOnce.
        Opção A: Crie um novo PV com accessMode ReadWriteMany:
          kubectl apply -f - <<EOF
          apiVersion: v1
          kind: PersistentVolume
          metadata:
            name: pv-rwx
          spec:
            capacity:
              storage: 1Gi
            accessModes: [ReadWriteMany]
            persistentVolumeReclaimPolicy: Retain
            hostPath:
              path: /mnt/data-rwx
          EOF
        Opção B: Delete o PVC e recrie-o com ReadWriteOnce.

Dica 4: Após o PVC fazer bind, o pod 'db' iniciará automaticamente."""


def deploy() -> tuple:
    kubectl(["create", "namespace", NS])
    r = apply_yaml("""\
apiVersion: v1
kind: PersistentVolume
metadata:
  name: scenario-19-pv
spec:
  capacity:
    storage: 500Mi
  accessModes:
  - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  hostPath:
    path: /mnt/scenario-19-data
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: db-storage
  namespace: scenario-19
spec:
  accessModes:
  - ReadWriteMany
  resources:
    requests:
      storage: 200Mi
---
apiVersion: v1
kind: Pod
metadata:
  name: db
  namespace: scenario-19
spec:
  containers:
  - name: db
    image: busybox:1.36
    command: ["sh", "-c", "echo DB Started; sleep 3600"]
    volumeMounts:
    - name: storage
      mountPath: /data
  volumes:
  - name: storage
    persistentVolumeClaim:
      claimName: db-storage
""")
    if r.returncode != 0:
        return False, r.stderr.strip()
    return True, "PV criado com ReadWriteOnce mas PVC solicita ReadWriteMany — não farão bind."


def verify() -> tuple:
    # Verificar se há algum PVC Bound no namespace (pode ser o original ou um novo)
    r = kubectl(["get", "pvc", "-n", NS,
                 "-o", "jsonpath={.items[*].status.phase}"])
    phases = r.stdout.strip().split()
    if not any(p == "Bound" for p in phases):
        return False, "Nenhum PVC está Bound no namespace scenario-19."

    # Verificar se o pod db está Running
    r2 = kubectl(["get", "pod", "db", "-n", NS,
                  "-o", "jsonpath={.status.phase}"])
    if r2.stdout.strip() == "Running":
        return True, "PVC Bound e pod 'db' está Running."
    return False, "PVC está Bound mas pod 'db' ainda não está Running."


def reset() -> tuple:
    delete_ns(NS)
    kubectl(["delete", "pv", "scenario-19-pv", "--ignore-not-found"])
    kubectl(["delete", "pv", "pv-rwx", "--ignore-not-found"])
    return True, f"Namespace {NS} e PVs removidos."
