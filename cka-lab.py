#!/usr/bin/env python3
"""CKA Lab CLI — equivalente aos scripts PowerShell, funciona no Windows e Linux."""

import argparse
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
VAGRANT_DIR = ROOT / "vagrant"
CONFIG_FILE = ROOT / "config" / "cluster.yaml"
OUTPUT_KUBECONFIG = ROOT / "output" / "kubeconfig" / "config"
SCENARIOS_DIR = ROOT / "scenarios"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _colors_supported() -> bool:
    if platform.system() == "Windows":
        # Windows Terminal e VS Code suportam ANSI; cmd.exe antigo não
        return "WT_SESSION" in os.environ or "TERM_PROGRAM" in os.environ or "ANSICON" in os.environ
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def info(msg: str) -> None:
    prefix = f"{CYAN}[info]{RESET} " if _colors_supported() else "[info] "
    print(prefix + msg)


def ok(msg: str) -> None:
    prefix = f"{GREEN}[ok]{RESET} " if _colors_supported() else "[ok] "
    print(prefix + msg)


def warn(msg: str) -> None:
    prefix = f"{YELLOW}[warn]{RESET} " if _colors_supported() else "[warn] "
    print(prefix + msg)


def error(msg: str) -> None:
    prefix = f"{RED}[error]{RESET} " if _colors_supported() else "[error] "
    print(prefix + msg, file=sys.stderr)


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        error(f"Arquivo de configuração não encontrado: {CONFIG_FILE}")
        sys.exit(1)
    with CONFIG_FILE.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _vagrant_query(*args: str) -> subprocess.CompletedProcess:
    """Roda vagrant capturando a saída — usado para leitura de estado, não para output ao vivo."""
    return subprocess.run(
        ["vagrant", *args],
        cwd=VAGRANT_DIR,
        capture_output=True,
        text=True,
        check=False,
    )


def vagrant_run(*args: str, check: bool = True) -> int:
    """Roda vagrant com output ao vivo e Ctrl+C funcional."""
    cmd = ["vagrant", *args]
    info(f"Executando: {' '.join(cmd)}")

    kwargs: dict = {"cwd": str(VAGRANT_DIR)}
    if platform.system() == "Windows":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    proc = subprocess.Popen(cmd, **kwargs)
    try:
        proc.wait()
    except KeyboardInterrupt:
        print()
        warn("Ctrl+C detectado — encerrando Vagrant...")
        _kill_proc(proc)
        sys.exit(130)

    if check and proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd)
    return proc.returncode


def _kill_proc(proc: subprocess.Popen) -> None:
    import signal as _signal
    try:
        if platform.system() == "Windows":
            proc.send_signal(_signal.CTRL_BREAK_EVENT)
        else:
            proc.terminate()
        proc.wait(timeout=10)
    except (subprocess.TimeoutExpired, OSError):
        proc.kill()


# ---------------------------------------------------------------------------
# Estado das VMs
# ---------------------------------------------------------------------------

# Estados possíveis do vagrant: running | poweroff | aborted | saved | not_created
_SKIP_STATES = {"running"}


def _get_vm_states() -> dict:
    """Retorna {nome_vm: estado} para todas as VMs definidas no Vagrantfile."""
    result = _vagrant_query("status", "--machine-readable")
    states = {}
    for line in result.stdout.splitlines():
        parts = line.split(",")
        if len(parts) >= 4 and parts[2] == "state":
            states[parts[1]] = parts[3]
    return states


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------

def cmd_up(_args) -> None:
    _preflight_check()

    states = _get_vm_states()

    if states:
        info("Estado atual das VMs:")
        for name, state in states.items():
            if state in _SKIP_STATES:
                ok(f"  {name}: {state} — já está rodando, será ignorado")
            else:
                warn(f"  {name}: {state}")
        print()

    to_start = [name for name, state in states.items() if state not in _SKIP_STATES]

    if states and not to_start:
        ok("Todas as VMs já estão rodando. Nada a fazer.")
        return

    if to_start:
        info(f"VMs a iniciar: {', '.join(to_start)}")
        for vm in to_start:
            info(f"Subindo {vm}...")
            vagrant_run("up", vm)
    else:
        info("Subindo o laboratório Kubernetes...")
        vagrant_run("up")

    ok("Cluster iniciado.")


def cmd_down(_args) -> None:
    states = _get_vm_states()
    running = [name for name, state in states.items() if state == "running"]

    if not running:
        ok("Nenhuma VM rodando. Nada a fazer.")
        return

    info(f"Desligando: {', '.join(running)}")
    vagrant_run("halt")
    ok("VMs desligadas. Os dados foram preservados.")
    info("Para ligar novamente: python cka-lab.py up")


def cmd_destroy(args) -> None:
    cmd = ["destroy"]
    if args.force:
        cmd.append("-f")
    vagrant_run(*cmd)
    ok("VMs destruídas.")


def cmd_status(_args) -> None:
    states = _get_vm_states()
    if states:
        info("Estado das VMs:\n")
        for name, state in states.items():
            if state == "running":
                ok(f"  {name}: {state}")
            elif state == "not_created":
                print(f"  {name}: {state}")
            else:
                warn(f"  {name}: {state}")
    else:
        vagrant_run("status")


def cmd_validate_network(_args) -> None:
    config = load_config()
    configured = config.get("network", {}).get("bridge_interface", "<não definida>")

    info("Interfaces de rede disponíveis no host:\n")

    if platform.system() == "Windows":
        subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                "Get-NetAdapter | Sort-Object Status, Name | "
                "Format-Table -AutoSize Name, InterfaceDescription, Status, LinkSpeed, MacAddress",
            ],
            check=False,
        )
    else:
        result = subprocess.run(["ip", "-o", "link", "show"], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    print(f"  {parts[1].rstrip(':')}")
        else:
            subprocess.run(["ifconfig", "-a"], check=False)

    print()
    info(f"Interface configurada em cluster.yaml: '{configured}'")
    warn("Ajuste network.bridge_interface com o nome exato da interface desejada.")


DEFAULT_KUBECONFIG = Path.home() / ".kube" / "config"


def _cp_name() -> str:
    config = load_config()
    cps = config.get("nodes", {}).get("control_planes", [])
    return cps[0]["name"] if cps else "cp-1"


def _cp_host_only_ip() -> str:
    config = load_config()
    base = config.get("network", {}).get("host_only_base", "192.168.99")
    return f"{base}.10"


def _fetch_kubeconfig() -> str:
    result = subprocess.run(
        ["vagrant", "ssh", _cp_name(), "-c", "sudo cat /etc/kubernetes/admin.conf"],
        cwd=VAGRANT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    if not result.stdout.strip():
        error("Saída vazia — o cluster pode ainda não estar inicializado.")
        sys.exit(1)

    raw = result.stdout
    cfg = yaml.safe_load(raw)

    # Garante que o servidor aponta para o IP host-only, não para o NAT (10.0.2.15)
    correct_ip = _cp_host_only_ip()
    changed = False
    for cluster in cfg.get("clusters", []):
        server = cluster.get("cluster", {}).get("server", "")
        if server and not server.startswith(f"https://{correct_ip}"):
            fixed = re.sub(r"https://[\d.]+:(\d+)", f"https://{correct_ip}:\\1", server)
            cluster["cluster"]["server"] = fixed
            warn(f"  IP do servidor corrigido: {server} → {fixed}")
            changed = True

    if changed:
        return yaml.dump(cfg, default_flow_style=False, allow_unicode=True)
    return raw


def _merge_kubeconfig(new_cfg: dict, dst: Path) -> None:
    """Faz merge do novo kubeconfig no destino, sobrescrevendo entradas de mesmo nome."""
    if dst.exists():
        with dst.open(encoding="utf-8") as f:
            existing = yaml.safe_load(f) or {}
    else:
        existing = {
            "apiVersion": "v1",
            "kind": "Config",
            "clusters": [],
            "contexts": [],
            "users": [],
            "preferences": {},
            "current-context": "",
        }

    def _upsert_list(key: str) -> None:
        existing_by_name = {e["name"]: i for i, e in enumerate(existing.get(key, []))}
        for entry in new_cfg.get(key, []):
            if entry["name"] in existing_by_name:
                existing[key][existing_by_name[entry["name"]]] = entry
                ok(f"  {key[:-1]} '{entry['name']}' atualizado")
            else:
                existing.setdefault(key, []).append(entry)
                ok(f"  {key[:-1]} '{entry['name']}' adicionado")

    _upsert_list("clusters")
    _upsert_list("contexts")
    _upsert_list("users")

    if new_cfg.get("current-context"):
        existing["current-context"] = new_cfg["current-context"]

    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8") as f:
        yaml.dump(existing, f, default_flow_style=False, allow_unicode=True)


def cmd_export_kubeconfig(_args) -> None:
    info(f"Exportando kubeconfig do control plane ({_cp_name()})...")
    raw = _fetch_kubeconfig()
    new_cfg = yaml.safe_load(raw)

    # 1. Salva cópia local no output/ do projeto
    OUTPUT_KUBECONFIG.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_KUBECONFIG.write_text(raw, encoding="utf-8")
    ok(f"Salvo em: {OUTPUT_KUBECONFIG}")

    # 2. Faz merge no ~/.kube/config padrão do usuário
    info(f"Fazendo merge em: {DEFAULT_KUBECONFIG}")
    _merge_kubeconfig(new_cfg, DEFAULT_KUBECONFIG)
    ok(f"Merge concluído em: {DEFAULT_KUBECONFIG}")

    ctx = new_cfg.get("current-context", "")
    if ctx:
        info(f"Para ativar este cluster: kubectl config use-context {ctx}")


# ---------------------------------------------------------------------------
# Validações de pré-condição
# ---------------------------------------------------------------------------

MIN_VAGRANT = (2, 3, 0)
MIN_VIRTUALBOX = (6, 1, 0)


def _parse_version(text: str) -> tuple:
    nums = re.findall(r"\d+", text)
    return tuple(int(n) for n in nums[:3]) if nums else (0, 0, 0)


def _fmt_version(t: tuple) -> str:
    return ".".join(str(x) for x in t)


def _resolve_cmd(cmd: list) -> list:
    """No Windows, tenta encontrar o executável em caminhos padrão se não estiver no PATH."""
    if platform.system() != "Windows":
        return cmd
    fallbacks = {
        "VBoxManage": [
            r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe",
            r"C:\Program Files (x86)\Oracle\VirtualBox\VBoxManage.exe",
        ],
    }
    exe = cmd[0]
    if exe in fallbacks:
        for path in fallbacks[exe]:
            if Path(path).exists():
                return [path] + cmd[1:]
    return cmd


def _check_tool(label: str, cmd: list, min_ver: tuple) -> bool:
    cmd = _resolve_cmd(cmd)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        error(f"{label} não encontrado — instale antes de continuar.")
        return False
    if result.returncode != 0 or not result.stdout.strip():
        error(f"{label} não encontrado no PATH — instale antes de continuar.")
        return False
    ver = _parse_version(result.stdout)
    if ver < min_ver:
        warn(f"{label} {_fmt_version(ver)} encontrado — versão mínima recomendada: {_fmt_version(min_ver)}")
    else:
        ok(f"{label} {_fmt_version(ver)}")
    return True


def _check_ram() -> None:
    try:
        config = load_config()
        nodes_cfg = config.get("nodes", {})
        all_nodes = (nodes_cfg.get("control_planes") or []) + (nodes_cfg.get("workers") or [])
        required_mb = sum(n.get("memory_mb", 0) for n in all_nodes)
        total_mb = 0

        if platform.system() == "Windows":
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory"],
                capture_output=True, text=True, check=False,
            )
            if r.returncode == 0 and r.stdout.strip():
                total_mb = int(r.stdout.strip()) // (1024 * 1024)
        elif platform.system() == "Linux":
            r = subprocess.run(["grep", "MemTotal", "/proc/meminfo"],
                               capture_output=True, text=True, check=False)
            if r.returncode == 0:
                total_mb = int(r.stdout.split()[1]) // 1024
        else:
            return

        if not total_mb:
            return

        if total_mb < required_mb:
            warn(
                f"RAM total: {total_mb} MB — cluster requer ~{required_mb} MB. "
                "Pode ficar lento ou falhar."
            )
        else:
            ok(f"RAM: {total_mb} MB total, cluster requer ~{required_mb} MB")
    except Exception as e:
        warn(f"Verificação de RAM ignorada: {e}")


def _preflight_check() -> None:
    info("Verificando pré-requisitos...\n")
    failed = []

    if not _check_tool("Vagrant", ["vagrant", "--version"], MIN_VAGRANT):
        failed.append("Vagrant")

    if not _check_tool("VirtualBox (VBoxManage)", ["VBoxManage", "--version"], MIN_VIRTUALBOX):
        failed.append("VirtualBox")

    if CONFIG_FILE.exists():
        ok(f"config/cluster.yaml encontrado")
    else:
        error(f"config/cluster.yaml não encontrado em {CONFIG_FILE}")
        failed.append("config/cluster.yaml")

    if (VAGRANT_DIR / "Vagrantfile").exists():
        ok("Vagrantfile encontrado")
    else:
        error(f"Vagrantfile não encontrado em {VAGRANT_DIR}")
        failed.append("Vagrantfile")

    _check_ram()

    print()

    if failed:
        error(f"Pré-requisitos com problema: {', '.join(failed)}")
        sys.exit(1)

    ok("Todos os pré-requisitos OK.\n")


# ---------------------------------------------------------------------------
# Cenários de simulação
# ---------------------------------------------------------------------------

_CATEGORY_COLORS = {
    "Troubleshooting": RED,
    "Architecture":    CYAN,
    "Networking":      GREEN,
    "Workloads":       YELLOW,
    "Storage":         MAGENTA,
}

_CAT_ORDER = ["Troubleshooting", "Architecture", "Networking", "Workloads", "Storage"]


def _load_all_scenarios() -> list:
    import importlib.util
    sys.path.insert(0, str(ROOT))
    mods = []
    if not SCENARIOS_DIR.exists():
        return mods
    for path in sorted(SCENARIOS_DIR.glob("s??_*.py")):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
            mods.append(mod)
        except Exception as exc:
            warn(f"Erro ao carregar {path.name}: {exc}")
    return mods


def _find_scenario(sid: str):
    for mod in _load_all_scenarios():
        mid = mod.METADATA["id"]
        num = mid.split("-")[0]
        if mid == sid or num == sid.zfill(2):
            return mod
    return None


def cmd_scenario(args) -> None:
    subcmd = getattr(args, "subcmd", "list")

    if subcmd == "list" or subcmd is None:
        _sc_list()
    elif subcmd == "deploy":
        _sc_action(args.id, "deploy")
    elif subcmd == "verify":
        _sc_action(args.id, "verify")
    elif subcmd == "reset":
        _sc_action(args.id, "reset")
    elif subcmd == "hint":
        _sc_hint(args.id)


def _sc_list() -> None:
    mods = _load_all_scenarios()
    if not mods:
        warn("Nenhum cenário encontrado em scenarios/")
        return

    by_cat: dict = {}
    for mod in mods:
        cat = mod.METADATA.get("category", "Outro")
        by_cat.setdefault(cat, []).append(mod)

    total = sum(len(v) for v in by_cat.values())
    print()
    info(f"{total} cenários disponíveis\n")

    for cat in _CAT_ORDER:
        if cat not in by_cat:
            continue
        col = _CATEGORY_COLORS.get(cat, RESET)
        if _colors_supported():
            print(f"{col}{BOLD}  {cat}{RESET}")
        else:
            print(f"  {cat}")
        print(f"  {'-' * 60}")
        for mod in by_cat[cat]:
            m = mod.METADATA
            diff_tag = {"iniciante": "[  ]", "intermediario": "[ *]", "avancado": "[**]"}.get(
                m.get("difficulty", ""), "[  ]")
            print(f"  {diff_tag}  {m['id']:<30}  {m['title']}")
        print()

    print("  Dificuldade:  [  ] iniciante   [ *] intermediário   [**] avançado\n")
    info("Comandos:")
    info("  python cka-lab.py scenario deploy <id>   — implanta o cenário")
    info("  python cka-lab.py scenario verify <id>   — verifica sua solução")
    info("  python cka-lab.py scenario hint   <id>   — exibe uma dica")
    info("  python cka-lab.py scenario reset  <id>   — desfaz o cenário")
    print()


def _sc_action(sid: str, action: str) -> None:
    mod = _find_scenario(sid)
    if not mod:
        error(f"Cenário '{sid}' não encontrado. Use 'python cka-lab.py scenario list'.")
        sys.exit(1)

    m = mod.METADATA
    col = _CATEGORY_COLORS.get(m.get("category", ""), RESET)

    print()
    if _colors_supported():
        info(f"{col}{BOLD}[{m['id']}]{RESET} {m['title']}  "
             f"({m.get('category','')}, {m.get('difficulty','')})")
    else:
        info(f"[{m['id']}] {m['title']}  ({m.get('category','')}, {m.get('difficulty','')})")
    print()

    if action == "deploy":
        print(mod.DESCRIPTION)
        print()
        info("Implantando cenário no cluster...")
        success, msg = mod.deploy()
        print()
        if success:
            ok(msg)
            print()
            warn("Resolva o problema descrito acima.")
            info(f"Quando terminar: python cka-lab.py scenario verify {m['id']}")
        else:
            error(f"Falha ao implantar: {msg}")
            sys.exit(1)

    elif action == "verify":
        info("Verificando solução...")
        success, msg = mod.verify()
        print()
        if success:
            ok(f"CORRETO! {msg}")
            info(f"Desfaça o cenário quando quiser: python cka-lab.py scenario reset {m['id']}")
        else:
            error(f"Ainda não está correto: {msg}")
            info(f"Precisa de ajuda? python cka-lab.py scenario hint {m['id']}")

    elif action == "reset":
        info("Desfazendo cenário...")
        success, msg = mod.reset()
        print()
        if success:
            ok(f"Cenário revertido. {msg}")
        else:
            error(f"Erro ao reverter: {msg}")


def _sc_hint(sid: str) -> None:
    mod = _find_scenario(sid)
    if not mod:
        error(f"Cenário '{sid}' não encontrado.")
        sys.exit(1)
    m = mod.METADATA
    print()
    info(f"Dica — [{m['id']}] {m['title']}\n")
    print(mod.HINT)
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="lab",
        description="CKA Lab CLI — gerencia o cluster Kubernetes local",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="<comando>")

    sub.add_parser("up", help="Sobe todas as VMs e inicializa o cluster")
    sub.add_parser("down", help="Desliga as VMs sem destruir (preserva dados)")

    p_destroy = sub.add_parser("destroy", help="Destrói as VMs do laboratório")
    p_destroy.add_argument("-f", "--force", action="store_true", help="Sem confirmação interativa")

    sub.add_parser("status", help="Exibe o status atual das VMs")
    sub.add_parser("validate-network", help="Lista as interfaces de rede disponíveis no host")
    sub.add_parser("export-kubeconfig", help="Exporta o kubeconfig do control plane para output/kubeconfig/config")

    p_sc = sub.add_parser("scenario", help="Gerencia cenários de simulação do exame CKA")
    sub_sc = p_sc.add_subparsers(dest="subcmd", metavar="<ação>")
    sub_sc.add_parser("list", help="Lista todos os cenários disponíveis")
    for _action, _help in [
        ("deploy", "Implanta um cenário (quebra o ambiente)"),
        ("verify", "Verifica se o cenário foi resolvido"),
        ("reset",  "Desfaz o cenário e limpa o cluster"),
        ("hint",   "Exibe uma dica para o cenário"),
    ]:
        _p = sub_sc.add_parser(_action, help=_help)
        _p.add_argument("id", help="ID do cenário (ex: 01-node-notready ou 01)")

    args = parser.parse_args()

    dispatch = {
        "up": cmd_up,
        "down": cmd_down,
        "destroy": cmd_destroy,
        "status": cmd_status,
        "validate-network": cmd_validate_network,
        "export-kubeconfig": cmd_export_kubeconfig,
        "scenario": cmd_scenario,
    }

    try:
        dispatch[args.command](args)
    except subprocess.CalledProcessError as exc:
        error(f"Comando falhou com código {exc.returncode}.")
        sys.exit(exc.returncode)
    except KeyboardInterrupt:
        print()
        warn("Interrompido pelo usuário.")
        sys.exit(130)


if __name__ == "__main__":
    main()
