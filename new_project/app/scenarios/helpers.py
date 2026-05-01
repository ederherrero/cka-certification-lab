"""Utilitários compartilhados — usa SSH direto nos nodes (sem vagrant)."""

import os
import subprocess
import tempfile
import time
from pathlib import Path

import yaml

SSH_KEY  = os.getenv("SSH_KEY",  "/home/vagrant/.ssh/lab_key")
SSH_USER = os.getenv("SSH_USER", "vagrant")
HOST_ONLY_BASE = os.getenv("HOST_ONLY_BASE", "192.168.99")

_NODE_IPS = {
    "cp-1": f"{HOST_ONLY_BASE}.10",
    "wk-1": f"{HOST_ONLY_BASE}.11",
    "wk-2": f"{HOST_ONLY_BASE}.12",
    "wk-3": f"{HOST_ONLY_BASE}.13",
}

ROOT = Path(__file__).resolve().parent.parent


def _cluster_cfg() -> dict:
    cfg = ROOT / "config" / "cluster.yaml"
    if cfg.exists():
        with cfg.open() as f:
            return yaml.safe_load(f)
    return {"cluster_name": "cka-lab"}


def cluster_name() -> str:
    return _cluster_cfg().get("cluster_name", "cka-lab")


def node_name(short: str) -> str:
    return f"{cluster_name()}-{short}"


# ---------------------------------------------------------------------------
# kubectl
# ---------------------------------------------------------------------------

def kubectl(args: list) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.setdefault("KUBECONFIG", "/home/vagrant/.kube/config")
    return subprocess.run(
        ["kubectl"] + args,
        capture_output=True, text=True, check=False, env=env,
    )


def apply_yaml(yaml_str: str) -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml",
                                     delete=False, encoding="utf-8") as f:
        f.write(yaml_str)
        tmp = f.name
    try:
        env = os.environ.copy()
        env.setdefault("KUBECONFIG", "/home/vagrant/.kube/config")
        return subprocess.run(
            ["kubectl", "apply", "-f", tmp],
            capture_output=True, text=True, check=False, env=env,
        )
    finally:
        os.unlink(tmp)


def delete_ns(ns: str) -> None:
    kubectl(["delete", "namespace", ns, "--ignore-not-found"])


# ---------------------------------------------------------------------------
# SSH direto nos nodes
# ---------------------------------------------------------------------------

def vssh(node_short: str, cmd: str) -> subprocess.CompletedProcess:
    """SSH direto no node via IP da rede host-only (substitui vagrant ssh)."""
    ip = _NODE_IPS.get(node_short)
    if not ip:
        result = subprocess.CompletedProcess(args=cmd, returncode=1)
        result.stdout = ""
        result.stderr = f"Node '{node_short}' não reconhecido. IPs: {_NODE_IPS}"
        return result

    return subprocess.run(
        [
            "ssh",
            "-i", SSH_KEY,
            "-o", "StrictHostKeyChecking=no",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=10",
            f"{SSH_USER}@{ip}",
            cmd,
        ],
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
