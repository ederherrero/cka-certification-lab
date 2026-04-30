"""Utilitários compartilhados entre todos os cenários."""

import subprocess
import tempfile
import os
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
VAGRANT_DIR = ROOT / "vagrant"


def _cluster_cfg() -> dict:
    with (ROOT / "config" / "cluster.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def cluster_name() -> str:
    return _cluster_cfg().get("cluster_name", "cka-certification-lab")


def node_name(short: str) -> str:
    """'wk-2' → 'cka-certification-lab-wk-2'"""
    return f"{cluster_name()}-{short}"


# ---------------------------------------------------------------------------
# kubectl helpers
# ---------------------------------------------------------------------------

def kubectl(args: list) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["kubectl"] + args,
        capture_output=True, text=True, check=False,
    )


def apply_yaml(yaml_str: str) -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml",
                                     delete=False, encoding="utf-8") as f:
        f.write(yaml_str)
        tmp = f.name
    try:
        return subprocess.run(
            ["kubectl", "apply", "-f", tmp],
            capture_output=True, text=True, check=False,
        )
    finally:
        os.unlink(tmp)


def delete_ns(ns: str) -> None:
    kubectl(["delete", "namespace", ns, "--ignore-not-found"])


# ---------------------------------------------------------------------------
# vagrant ssh helpers
# ---------------------------------------------------------------------------

def vssh(node_short: str, cmd: str) -> subprocess.CompletedProcess:
    """Executa comando via vagrant ssh no node especificado."""
    return subprocess.run(
        ["vagrant", "ssh", node_short, "-c", cmd],
        cwd=str(VAGRANT_DIR),
        capture_output=True, text=True, check=False,
    )


# ---------------------------------------------------------------------------
# Estado do cluster
# ---------------------------------------------------------------------------

def node_ready(short: str) -> bool:
    r = kubectl(["get", "node", node_name(short),
                 "-o", "jsonpath={.status.conditions[?(@.type=='Ready')].status}"])
    return r.stdout.strip() == "True"


def pod_phase(name: str, ns: str = "default") -> str:
    r = kubectl(["get", "pod", name, "-n", ns,
                 "-o", "jsonpath={.status.phase}"])
    return r.stdout.strip()


def all_pods_running_in_ns(ns: str) -> bool:
    r = kubectl(["get", "pods", "-n", ns,
                 "-o", "jsonpath={.items[*].status.phase}"])
    phases = r.stdout.strip().split()
    return bool(phases) and all(p == "Running" for p in phases)


def deployment_ready(name: str, ns: str = "default") -> bool:
    r = kubectl(["get", "deployment", name, "-n", ns,
                 "-o", "jsonpath={.status.availableReplicas}"])
    avail = r.stdout.strip()
    r2 = kubectl(["get", "deployment", name, "-n", ns,
                  "-o", "jsonpath={.spec.replicas}"])
    desired = r2.stdout.strip()
    return bool(avail) and bool(desired) and avail == desired


def endpoints_filled(svc: str, ns: str = "default") -> bool:
    r = kubectl(["get", "endpoints", svc, "-n", ns,
                 "-o", "jsonpath={.subsets[0].addresses[0].ip}"])
    return bool(r.stdout.strip())


def pvc_bound(name: str, ns: str = "default") -> bool:
    r = kubectl(["get", "pvc", name, "-n", ns,
                 "-o", "jsonpath={.status.phase}"])
    return r.stdout.strip() == "Bound"


def can_i(verb: str, resource: str, ns: str, sa_ns: str, sa: str) -> bool:
    r = kubectl(["auth", "can-i", verb, resource, "-n", ns,
                 f"--as=system:serviceaccount:{sa_ns}:{sa}"])
    return r.returncode == 0 and r.stdout.strip() == "yes"


def exec_in_pod(pod: str, ns: str, cmd: str) -> subprocess.CompletedProcess:
    return kubectl(["exec", pod, "-n", ns, "--", "sh", "-c", cmd])


def wait_for(check_fn, timeout: int = 120, interval: int = 5) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if check_fn():
            return True
        time.sleep(interval)
    return False
