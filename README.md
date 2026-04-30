# CKA Certification Lab

Laboratório Kubernetes local para estudo da certificação **CKA (Certified Kubernetes Administrator)**.

Sobe um cluster real com `kubeadm` em VMs VirtualBox, operado por uma CLI Python simples. Toda a configuração fica em um único arquivo YAML — sem precisar editar Vagrantfile ou scripts de bootstrap.

---

## Como funciona

```
Você edita config/cluster.yaml
         │
         ▼
python lab.py up
         │
         ▼
Vagrant cria as VMs no VirtualBox
         │
         ├─► cp-1  → bootstrap-common.sh   (containerd + kubeadm)
         │          → bootstrap-control-plane.sh  (kubeadm init + Calico)
         │
         ├─► wk-1  → bootstrap-common.sh
         │          → bootstrap-worker.sh   (kubeadm join)
         │
         └─► wk-N  → (mesmo processo)
```

Cada VM tem três interfaces de rede:

| Interface | Tipo | IP | Para que serve |
|---|---|---|---|
| eth0 | NAT | 10.0.2.15 | Internet dentro da VM (baixar pacotes) |
| eth1 | Host-only | 192.168.99.10 / .11 / .12 | Acesso do host às VMs (kubectl) |
| eth2 | Bridge | DHCP da sua LAN | Visibilidade na rede local |

O `kubectl` do host acessa o cluster pelo IP host-only (`192.168.99.10`), que é estático e não muda.

---

## Pré-requisitos

### Software

| Ferramenta | Versão mínima | Instalação |
|---|---|---|
| Oracle VirtualBox | 6.1 | [virtualbox.org](https://www.virtualbox.org) |
| Vagrant | 2.3 | [vagrantup.com](https://www.vagrantup.com) |
| Python | 3.10 | [python.org](https://www.python.org) |
| kubectl | qualquer | [kubernetes.io/docs/tasks/tools](https://kubernetes.io/docs/tasks/tools) |

### Hardware

| Recurso | Mínimo | Recomendado |
|---|---|---|
| RAM | 16 GB | 32 GB |
| CPU | 4 cores com VT-x/AMD-V | 8+ cores |
| Disco livre | 60 GB | 100 GB |

> A configuração padrão (1 control plane + 2 workers) reserva ~10 GB de RAM.

---

## Imagem das VMs (Vagrant Box)

| Box | Ubuntu | Alinhamento CKA | Observação |
|---|---|---|---|
| `bento/ubuntu-22.04` | 22.04 Jammy | ✅ **Recomendada** | Mesma versão do ambiente do exame |
| `bento/ubuntu-24.04` | 24.04 Noble | ⚠️ Funciona | Mais nova que o exame, pode ter diferenças |
| `ubuntu/jammy64` | 22.04 Jammy | ✅ Oficial Canonical | Mais pesada, problemas ocasionais com guest additions |
| `generic/ubuntu2204` | 22.04 Jammy | ✅ Boa alternativa | Bem mantida, boa compatibilidade |

As boxes **bento** são mantidas pela Chef Software — minimalistas, leves e atualizadas regularmente. São a escolha mais estável para Vagrant + VirtualBox.

Este projeto usa `bento/ubuntu-22.04` por ser a versão alinhada com o ambiente real do exame CKA.

---

## Estrutura do projeto

```
cka-certification-lab/
├── lab.py                          ← CLI principal
├── requirements.txt                ← dependência Python (pyyaml)
├── config/
│   └── cluster.yaml                ← ÚNICO arquivo que você edita
├── vagrant/
│   ├── Vagrantfile                 ← lê cluster.yaml e define as VMs
│   └── scripts/
│       ├── bootstrap-common.sh     ← instalado em todos os nodes
│       ├── bootstrap-control-plane.sh
│       └── bootstrap-worker.sh
├── output/
│   └── kubeconfig/
│       └── config                  ← gerado pelo export-kubeconfig
└── old/                            ← arquivos não utilizados (referência)
```

---

## Configuração (cluster.yaml)

Abra `config/cluster.yaml`. Este é o único arquivo que você precisa editar.

```yaml
cluster_name: cka-certification-lab

# Imagem das VMs — bento/ubuntu-22.04 alinhada com o ambiente do exame CKA
box:
  name: bento/ubuntu-22.04
  version: ">= 0"

provider:
  name: virtualbox

# Rede — ajuste bridge_interface com o nome exato da sua placa de rede
network:
  bridge_interface: "Intel(R) Ethernet Connection (2) I219-V"
  nat_enabled: true
  ip_mode: dhcp
  host_only_base: "192.168.99"   # não altere sem necessidade

# Versão do Kubernetes instalada nos nodes
kubernetes:
  version: "1.34"
  pod_cidr: "10.244.0.0/16"
  service_cidr: "10.96.0.0/12"
  cni: calico
  cri: containerd

# Versões dos addons instalados no cluster
addons:
  calico:
    version: "3.30.2"
  metrics_server:
    enabled: false
    version: "0.7.2"

# Nodes do cluster — nome, vCPUs e RAM individuais por node
nodes:
  control_planes:
    - name: cp-1
      cpus: 2
      memory_mb: 4096

  workers:
    - name: wk-1
      cpus: 2
      memory_mb: 3072
    - name: wk-2
      cpus: 2
      memory_mb: 3072

access:
  export_kubeconfig: true
  ssh_user: vagrant
```

---

## Passo a passo: subindo o cluster do zero

### 1. Clonar o repositório

```bash
git clone <url-do-repositorio>
cd cka-certification-lab
```

### 2. Instalar dependência Python

```bash
pip install -r requirements.txt
```

### 3. Descobrir o nome da interface de rede

```bash
python lab.py validate-network
```

Saída esperada:

```
[info] Interfaces de rede disponíveis no host:

Name       InterfaceDescription                          Status  LinkSpeed
----       --------------------                          ------  ---------
Ethernet   Intel(R) Ethernet Connection (2) I219-V       Up      1 Gbps
Wi-Fi      Qualcomm Atheros AR938x Wireless Adapter      Disconnected  0 bps

[info] Interface configurada em cluster.yaml: 'Intel(R) Ethernet Connection'
[warn] Ajuste network.bridge_interface com o nome exato da interface desejada.
```

Copie o valor da coluna **Name** da interface com status **Up** conectada à internet e cole exatamente em `config/cluster.yaml`:

```yaml
network:
  bridge_interface: "Intel(R) Ethernet Connection (2) I219-V"
```

### 4. Subir o cluster

```bash
python lab.py up
```

O script verifica os pré-requisitos automaticamente antes de subir qualquer VM:

```
[info] Verificando pré-requisitos...

[ok] Vagrant 2.4.9
[ok] VirtualBox (VBoxManage) 7.2.6
[ok] config/cluster.yaml encontrado
[ok] Vagrantfile encontrado
[ok] RAM: 32684 MB total, cluster requer ~10240 MB

[ok] Todos os pré-requisitos OK.

[info] Estado atual das VMs:
[warn]   cp-1: not_created
[warn]   wk-1: not_created
[warn]   wk-2: not_created

[info] VMs a iniciar: cp-1, wk-1, wk-2
```

> **Primeira execução:** o Vagrant baixa a box `bento/ubuntu-24.04` (~1 GB). Acontece só uma vez.

> **Pergunta sobre bridge:** se aparecer `Which interface should the network bridge to?`, digite `1` e Enter. Isso não acontece quando o nome da interface no `cluster.yaml` é exato.

O processo completo leva entre **10 e 20 minutos**.

### 5. Verificar o status das VMs

```bash
python lab.py status
```

```
[info] Estado das VMs:

[ok]   cp-1: running
[ok]   wk-1: running
[ok]   wk-2: running
```

### 6. Exportar o kubeconfig

```bash
python lab.py export-kubeconfig
```

```
[info] Exportando kubeconfig do control plane (cp-1)...
[ok]   Salvo em: output\kubeconfig\config
[info] Fazendo merge em: C:\Users\seu-usuario\.kube\config
[ok]   cluster 'kubernetes' atualizado
[ok]   context 'kubernetes-admin@kubernetes' atualizado
[ok]   user 'kubernetes-admin' atualizado
[ok]   Merge concluído em: C:\Users\seu-usuario\.kube\config
[info] Para ativar este cluster: kubectl config use-context kubernetes-admin@kubernetes
```

O kubeconfig é salvo em dois lugares:
- `output/kubeconfig/config` — cópia local do projeto
- `~/.kube/config` — arquivo padrão do kubectl (merge automático, preserva outros clusters)

### 7. Ativar o contexto do cluster

```bash
kubectl config use-context kubernetes-admin@kubernetes
```

### 8. Verificar os nodes

```bash
kubectl get nodes
```

```
NAME                         STATUS   ROLES           AGE   VERSION
cka-certification-lab-cp-1   Ready    control-plane   10m   v1.34.7
cka-certification-lab-wk-1   Ready    <none>          8m    v1.34.7
cka-certification-lab-wk-2   Ready    <none>          4m    v1.34.7
```

Cluster pronto para uso.

---

## Referência dos comandos

```bash
# Listar interfaces de rede do host
python lab.py validate-network

# Subir o cluster (verifica pré-requisitos e detecta VMs já criadas)
python lab.py up

# Ver estado atual das VMs
python lab.py status

# Exportar kubeconfig e fazer merge em ~/.kube/config
python lab.py export-kubeconfig

# Destruir as VMs (pede confirmação)
python lab.py destroy

# Destruir sem confirmação
python lab.py destroy --force

# Ajuda
python lab.py --help
```

---

## Operações comuns

### Recriar o cluster do zero

```bash
python lab.py destroy --force
python lab.py up
python lab.py export-kubeconfig
kubectl get nodes
```

### Adicionar um worker

Edite `config/cluster.yaml`:

```yaml
  workers:
    - name: wk-1
      cpus: 2
      memory_mb: 3072
    - name: wk-2
      cpus: 2
      memory_mb: 3072
    - name: wk-3        # ← novo
      cpus: 2
      memory_mb: 3072
```

```bash
python lab.py up        # sobe só o wk-3, ignora cp-1/wk-1/wk-2 que já estão rodando
```

### Nomear nodes para cenários CKA

```yaml
  workers:
    - name: node01
      cpus: 2
      memory_mb: 3072
    - name: node02
      cpus: 2
      memory_mb: 3072
```

### Desligar as VMs sem destruir

```bash
cd vagrant
vagrant halt
```

### Ligar novamente depois de halt

```bash
python lab.py up        # detecta VMs em poweroff e liga sem re-provisionar
```

### Acessar uma VM via SSH

```bash
cd vagrant
vagrant ssh cp-1
vagrant ssh wk-1
```

---

## Solução de problemas

### Vagrant pergunta qual interface usar

```
Which interface should the network bridge to?
1) Intel(R) Ethernet Connection (2) I219-V
2) Hyper-V Virtual Ethernet Adapter
```

Digite `1` e Enter. Para não perguntar mais, coloque o nome **exato** no `cluster.yaml` (com o sufixo completo).

---

### VBoxManage não encontrado

```
[error] VirtualBox (VBoxManage) não encontrado — instale antes de continuar.
```

O `lab.py` procura automaticamente em `C:\Program Files\Oracle\VirtualBox\`. Se ainda assim não encontrar, adicione ao PATH:

```powershell
# PowerShell como Administrador
[Environment]::SetEnvironmentVariable(
    "PATH",
    $env:PATH + ";C:\Program Files\Oracle\VirtualBox",
    "Machine"
)
```

Feche e abra o terminal depois.

---

### kubectl não conecta (`10.0.2.15`)

```
Get "https://10.0.2.15:6443/api?timeout=32s": dial tcp 10.0.2.15:6443: connect...
```

O kubeconfig está apontando para o IP NAT interno do VirtualBox. Rode:

```bash
python lab.py export-kubeconfig
```

O `lab.py` corrige o endereço automaticamente para `192.168.99.10` (IP host-only acessível).

---

### Erro de certificado TLS após recriar o cluster

```
tls: failed to verify certificate: x509: certificate signed by unknown authority
```

O kubeconfig tem o certificado do cluster antigo. Rode:

```bash
python lab.py export-kubeconfig
```

O merge atualiza a entrada existente com os novos certificados.

---

### Ctrl+C não para a execução

A partir da versão atual, Ctrl+C encerra o processo do Vagrant corretamente. Se o terminal travar mesmo assim, abra outro terminal e rode:

```bash
cd vagrant
vagrant halt
```

---

## Roadmap

**Concluído**
- [x] Configuração central em `cluster.yaml` (versões, nomes, recursos por node)
- [x] Vagrantfile dinâmico que lê a lista de nodes do YAML
- [x] Bootstrap via shell scripts (containerd + kubeadm + Calico)
- [x] Versões de addons configuráveis (Calico, Metrics Server)
- [x] CLI Python com validação de pré-requisitos (Vagrant, VirtualBox, RAM)
- [x] Detecção de estado das VMs — retoma sem recriar o que já existe
- [x] Ctrl+C funcional — encerra o Vagrant corretamente no Windows
- [x] Rede host-only com IPs estáticos (sem conflito de DHCP)
- [x] Export do kubeconfig com merge automático em `~/.kube/config`
- [x] Correção automática do IP e certificado no kubeconfig exportado

**Planejado**
- [ ] Export automático do kubeconfig ao final do `up`
- [ ] Detecção automática da interface bridge (sem precisar configurar manualmente)
- [ ] Cenários de estudo CKA prontos (RBAC, NetworkPolicy, PV/PVC)
- [ ] Ingress controller opcional (nginx)
- [ ] HA com 3 control planes
- [ ] Suporte a Linux host
