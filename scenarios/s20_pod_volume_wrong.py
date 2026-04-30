from scenarios.helpers import kubectl, apply_yaml, delete_ns, wait_for

METADATA = {
    "id": "20-pod-volume-wrong",
    "title": "Volume montado no path errado",
    "category": "Storage",
    "lab_ref": "labs/04-storage.md",
    "difficulty": "intermediario",
}

NS = "scenario-20"

DESCRIPTION = """\
╔══════════════════════════════════════════════════════════════════╗
║  CENÁRIO 20 — Volume montado no path errado                      ║
╠══════════════════════════════════════════════════════════════════╣
║  O pod 'logger' no namespace scenario-20 usa um PVC para         ║
║  persistir logs. Após reiniciar o pod, os logs somem.            ║
║                                                                  ║
║  TAREFA                                                          ║
║  Corrija o pod 'logger' para que os dados escritos em /logs      ║
║  sejam persistidos no PVC. Após a correção, reinicie o pod       ║
║  e verifique que os dados sobrevivem ao restart.                 ║
║                                                                  ║
║  Namespace: scenario-20                                          ║
╚══════════════════════════════════════════════════════════════════╝"""

HINT = """\
Dica 1: kubectl describe pod logger -n scenario-20
        Observe onde o volume está montado (Mounts).

Dica 2: O container escreve em /logs mas o volume está montado em /cache.
        Por isso os dados não são persistidos.

Dica 3: Pods não podem ser editados diretamente. Exporte e recrie:
        kubectl get pod logger -n scenario-20 -o yaml > /tmp/logger.yaml
        # Altere volumeMounts.mountPath de /cache para /logs
        kubectl delete pod logger -n scenario-20
        kubectl apply -f /tmp/logger.yaml

Dica 4: Verifique que os dados sobrevivem ao restart do pod:
        kubectl exec logger -n scenario-20 -- cat /logs/app.log
        kubectl delete pod logger -n scenario-20
        kubectl apply -f /tmp/logger.yaml
        kubectl exec logger -n scenario-20 -- cat /logs/app.log"""


def deploy() -> tuple:
    kubectl(["create", "namespace", NS])
    r = apply_yaml("""\
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: log-storage
  namespace: scenario-20
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 100Mi
---
apiVersion: v1
kind: Pod
metadata:
  name: logger
  namespace: scenario-20
spec:
  containers:
  - name: logger
    image: busybox:1.36
    command:
    - sh
    - -c
    - |
      mkdir -p /logs
      echo "$(date): app started" >> /logs/app.log
      while true; do
        echo "$(date): heartbeat" >> /logs/app.log
        sleep 10
      done
    volumeMounts:
    - name: log-vol
      mountPath: /cache
  volumes:
  - name: log-vol
    persistentVolumeClaim:
      claimName: log-storage
""")
    if r.returncode != 0:
        return False, r.stderr.strip()
    return True, "Pod 'logger' criado: escreve em /logs mas o volume está montado em /cache."


def verify() -> tuple:
    # Verificar se o pod está Running
    r = kubectl(["get", "pod", "logger", "-n", NS,
                 "-o", "jsonpath={.status.phase}"])
    if r.stdout.strip() != "Running":
        return False, "Pod 'logger' não está Running."

    # Verificar se o mountPath foi corrigido para /logs
    r2 = kubectl(["get", "pod", "logger", "-n", NS,
                  "-o", "jsonpath={.spec.containers[0].volumeMounts[0].mountPath}"])
    mount = r2.stdout.strip()
    if mount != "/logs":
        return False, f"Volume ainda montado em '{mount}' — deve ser '/logs'."

    # Verificar se há dados em /logs no pod
    r3 = kubectl(["exec", "logger", "-n", NS, "--",
                  "sh", "-c", "test -f /logs/app.log && echo exists"])
    if "exists" not in r3.stdout:
        return False, "Volume montado em /logs mas arquivo /logs/app.log não existe ainda."

    return True, "Volume montado em /logs e arquivo app.log presente — dados serão persistidos."


def reset() -> tuple:
    delete_ns(NS)
    return True, f"Namespace {NS} e PVC removidos."
