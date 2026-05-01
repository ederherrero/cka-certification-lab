from scenarios.helpers import kubectl, apply_yaml, delete_ns, deployment_ready

METADATA = {
    "id": "04-app-env-missing",
    "title": "Variável de ambiente ausente",
    "category": "Troubleshooting",
    "lab_ref": "labs/05-troubleshooting.md",
    "difficulty": "intermediario",
}

NS = "scenario-04"

DESCRIPTION = """\
╔══════════════════════════════════════════════════════════════════╗
║  CENÁRIO 04 — Variável de ambiente ausente                       ║
╠══════════════════════════════════════════════════════════════════╣
║  O Deployment 'api' no namespace scenario-04 não está iniciando. ║
║  A aplicação exige a variável DB_HOST para funcionar.            ║
║                                                                  ║
║  TAREFA                                                          ║
║  Identifique o problema e corrija o ConfigMap 'api-config' para  ║
║  que o Deployment 'api' tenha todos os pods em Running.          ║
║                                                                  ║
║  Namespace: scenario-04                                          ║
╚══════════════════════════════════════════════════════════════════╝"""

HINT = """\
Dica 1: kubectl describe pod -n scenario-04
        Veja a seção 'Environment' e 'Events'.

Dica 2: kubectl get configmap api-config -n scenario-04 -o yaml
        Compare as chaves presentes com as que o container referencia.

Dica 3: O container espera a chave 'DB_HOST' no ConfigMap 'api-config'.
        Adicione-a: kubectl edit configmap api-config -n scenario-04
        Valor sugerido: DB_HOST=postgres.scenario-04.svc.cluster.local

Dica 4: Após corrigir o ConfigMap, os pods precisam ser recriados:
        kubectl rollout restart deployment api -n scenario-04"""


def deploy() -> tuple:
    kubectl(["create", "namespace", NS])
    manifest = """\
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-config
  namespace: scenario-04
data:
  LOG_LEVEL: "info"
  PORT: "8080"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: scenario-04
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: busybox:1.36
        command:
        - sh
        - -c
        - |
          if [ -z "$DB_HOST" ]; then
            echo "ERRO: DB_HOST nao definida" >&2
            exit 1
          fi
          echo "Conectando em $DB_HOST"
          sleep 3600
        envFrom:
        - configMapRef:
            name: api-config
"""
    r = apply_yaml(manifest)
    if r.returncode != 0:
        return False, r.stderr.strip()
    return True, "ConfigMap 'api-config' criado sem a chave DB_HOST. Deployment 'api' falhando."


def verify() -> tuple:
    r = kubectl(["get", "configmap", "api-config", "-n", NS,
                 "-o", "jsonpath={.data.DB_HOST}"])
    if not r.stdout.strip():
        return False, "ConfigMap 'api-config' ainda não tem a chave DB_HOST."

    if deployment_ready("api", NS):
        return True, "ConfigMap corrigido e Deployment 'api' está com todos os pods Running."

    return False, "DB_HOST presente no ConfigMap mas pods ainda não estão Running. Tente: kubectl rollout restart deployment api -n scenario-04"


def reset() -> tuple:
    delete_ns(NS)
    return True, f"Namespace {NS} removido."
