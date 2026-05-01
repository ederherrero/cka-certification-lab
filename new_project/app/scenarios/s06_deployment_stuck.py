from scenarios.helpers import kubectl, apply_yaml, delete_ns

METADATA = {
    "id": "06-deployment-stuck",
    "title": "Deployment travado no rollout",
    "category": "Troubleshooting",
    "lab_ref": "labs/05-troubleshooting.md",
    "difficulty": "avancado",
}

NS = "scenario-06"

DESCRIPTION = """\
╔══════════════════════════════════════════════════════════════════╗
║  CENÁRIO 06 — Deployment travado no rollout                      ║
╠══════════════════════════════════════════════════════════════════╣
║  O Deployment 'frontend' no namespace scenario-06 foi atualizado ║
║  mas o rollout está parado e nunca termina.                      ║
║                                                                  ║
║  TAREFA                                                          ║
║  Identifique por que o rollout está travado e corrija a          ║
║  estratégia de atualização do Deployment para que o rollout      ║
║  conclua com sucesso.                                            ║
║                                                                  ║
║  Namespace: scenario-06                                          ║
╚══════════════════════════════════════════════════════════════════╝"""

HINT = """\
Dica 1: kubectl rollout status deployment frontend -n scenario-06
        O rollout está esperando alguma condição impossível?

Dica 2: kubectl describe deployment frontend -n scenario-06
        Leia a seção 'StrategyType' e 'RollingUpdateStrategy'.

Dica 3: Se maxSurge=0 e maxUnavailable=0 ao mesmo tempo, o Kubernetes
        não consegue criar novos pods (maxSurge=0) nem terminar os
        antigos (maxUnavailable=0). É um deadlock.

Dica 4: Corrija com:
        kubectl patch deployment frontend -n scenario-06 \\
          -p '{"spec":{"strategy":{"rollingUpdate":{"maxSurge":1,"maxUnavailable":0}}}}'"""


def deploy() -> tuple:
    kubectl(["create", "namespace", NS])

    manifest = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: scenario-06
spec:
  replicas: 3
  selector:
    matchLabels:
      app: frontend
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 0
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: nginx
        image: nginx:1.25
"""
    r = apply_yaml(manifest)
    if r.returncode != 0:
        return False, r.stderr.strip()

    import time
    time.sleep(5)

    kubectl(["set", "image", "deployment/frontend", "nginx=nginx:1.26", "-n", NS])

    return True, "Deployment 'frontend' atualizado com maxSurge=0 e maxUnavailable=0 — rollout está travado."


def verify() -> tuple:
    r = kubectl(["rollout", "status", "deployment/frontend", "-n", NS, "--timeout=5s"])
    if r.returncode == 0:
        return True, "Rollout do Deployment 'frontend' concluído com sucesso."

    r2 = kubectl(["get", "deployment", "frontend", "-n", NS,
                  "-o", "jsonpath={.spec.strategy.rollingUpdate.maxSurge}"])
    surge = r2.stdout.strip()
    r3 = kubectl(["get", "deployment", "frontend", "-n", NS,
                  "-o", "jsonpath={.spec.strategy.rollingUpdate.maxUnavailable}"])
    unavail = r3.stdout.strip()

    if surge == "0" and unavail == "0":
        return False, "Estratégia ainda tem maxSurge=0 e maxUnavailable=0. Rollout impossível."
    return False, f"Estratégia atualizada (maxSurge={surge}, maxUnavailable={unavail}) mas rollout ainda não terminou."


def reset() -> tuple:
    delete_ns(NS)
    return True, f"Namespace {NS} removido."
