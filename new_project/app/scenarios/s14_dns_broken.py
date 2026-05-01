from scenarios.helpers import kubectl, apply_yaml, delete_ns, wait_for

METADATA = {
    "id": "14-dns-broken",
    "title": "CoreDNS com ConfigMap corrompido",
    "category": "Networking",
    "lab_ref": "labs/03-services-networking.md",
    "difficulty": "avancado",
}

NS = "scenario-14"

GOOD_COREFILE = """\
.:53 {
    errors
    health {
       lameduck 5s
    }
    ready
    kubernetes cluster.local in-addr.arpa ip6.arpa {
       pods insecure
       fallthrough in-addr.arpa ip6.arpa
       ttl 30
    }
    prometheus :9153
    forward . /etc/resolv.conf {
       max_concurrent 1000
    }
    cache 30
    loop
    reload
    loadbalance
}
"""

BAD_COREFILE = """\
.:53 {
    errors
    health {
       lameduck 5s
    }
    ready
    kubernetes cluster.local in-addr.arpa ip6.arpa {
       pods insecure
       fallthrough in-addr.arpa ip6.arpa
       ttl 30
    }
    prometheus :9153
    forward . /etc/resolv.conf {
       max_concurrent 1000
    }
    cache 30
    loop
    reload
    loadbalance
    nonexistentplugin
}
"""

DESCRIPTION = """\
╔══════════════════════════════════════════════════════════════════╗
║  CENÁRIO 14 — CoreDNS com ConfigMap corrompido                   ║
╠══════════════════════════════════════════════════════════════════╣
║  Pods no cluster não conseguem resolver nomes DNS internos.      ║
║  O CoreDNS foi alterado recentemente e pode estar com problemas. ║
║                                                                  ║
║  TAREFA                                                          ║
║  Corrija o ConfigMap do CoreDNS (coredns em kube-system) para    ║
║  que a resolução DNS volte a funcionar no cluster.               ║
║  Valide criando o pod 'dns-test' no namespace scenario-14 e      ║
║  executando: nslookup kubernetes.default                         ║
║                                                                  ║
║  Namespace: kube-system (ConfigMap) / scenario-14 (validação)   ║
╚══════════════════════════════════════════════════════════════════╝"""

HINT = """\
Dica 1: kubectl get pods -n kube-system -l k8s-app=kube-dns
        Os pods do CoreDNS estão Running?

Dica 2: kubectl logs -n kube-system -l k8s-app=kube-dns
        Qual erro aparece nos logs?

Dica 3: kubectl edit configmap coredns -n kube-system
        Procure por entradas inválidas no Corefile.
        Remova qualquer plugin que não seja padrão do CoreDNS.

Dica 4: Após corrigir o ConfigMap, reinicie o CoreDNS:
        kubectl rollout restart deployment coredns -n kube-system

Dica 5: Teste:
        kubectl run dns-test --image=busybox:1.36 --rm -it --restart=Never \\
          -n scenario-14 -- nslookup kubernetes.default"""


def deploy() -> tuple:
    kubectl(["create", "namespace", NS])

    r = kubectl(["get", "configmap", "coredns", "-n", "kube-system",
                 "-o", "jsonpath={.data.Corefile}"])
    if r.returncode != 0:
        return False, "Não foi possível ler o ConfigMap do CoreDNS."

    bad_cm = f"""\
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
{_indent(BAD_COREFILE, 4)}
"""
    apply_yaml(bad_cm)
    kubectl(["rollout", "restart", "deployment", "coredns", "-n", "kube-system"])

    return True, "ConfigMap do CoreDNS corrompido com plugin inválido. Pods de CoreDNS falharão ao reiniciar."


def verify() -> tuple:
    r = kubectl(["get", "pods", "-n", "kube-system", "-l", "k8s-app=kube-dns",
                 "-o", "jsonpath={.items[*].status.phase}"])
    phases = r.stdout.strip().split()
    if not all(p == "Running" for p in phases):
        return False, f"Pods do CoreDNS ainda não estão todos Running: {phases}"

    r2 = kubectl(["run", "dns-verify", "--image=busybox:1.36", "--rm",
                  "--restart=Never", "-n", NS,
                  "--timeout=30s",
                  "--", "nslookup", "kubernetes.default"])
    if r2.returncode == 0 and "Address" in r2.stdout:
        return True, "CoreDNS restaurado. Resolução DNS funcionando."
    return False, "Pods CoreDNS Running mas DNS ainda não resolve. Verifique se reiniciou o deployment."


def _indent(s: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line for line in s.splitlines())


def reset() -> tuple:
    good_cm = f"""\
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
{_indent(GOOD_COREFILE, 4)}
"""
    apply_yaml(good_cm)
    kubectl(["rollout", "restart", "deployment", "coredns", "-n", "kube-system"])
    delete_ns(NS)
    return True, "ConfigMap do CoreDNS restaurado e CoreDNS reiniciado."
