# CKA Certification Lab

Laboratório Kubernetes local para estudo da certificação **CKA (Certified Kubernetes Administrator)**.

Sobe um cluster real com `kubeadm` em VMs VirtualBox, operado por uma CLI Python simples. Toda a configuração fica em um único arquivo YAML — sem precisar editar Vagrantfile ou scripts de bootstrap.

---

## Como funciona

```
Você edita config/cluster.yaml
         │
         ▼
python cka-lab.py up
         │
         ▼
Vagrant cria as VMs no VirtualBox
         │
         ├─► cp-1  → bootstrap-common.sh          (containerd + kubeadm)
         │          → bootstrap-control-plane.sh   (kubeadm init + Calico)
         │
         ├─► wk-1  → bootstrap-common.sh
         │          → bootstrap-worker.sh          (kubeadm join)
         │
         └─► wk-N  → (mesmo processo)
```

Cada VM tem três interfaces de rede:

| Interface | Tipo | IP | Para que serve |
|---|---|---|---|
| eth0 | NAT | 10.0.2.15 | Internet dentro da VM (baixar pacotes) |
| eth1 | Host-only | 192.168.99.10 / .11 / .12 ... | Acesso do host às VMs (kubectl) |
| eth2 | Bridge | DHCP da sua LAN | Visibilidade na rede local |

O `kubectl` acessa o cluster pelo IP host-only (`192.168.99.10`), que é estático e não muda.

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

> A configuração padrão (1 control plane + 4 workers) reserva ~16 GB de RAM.

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
├── cka-lab.py                          ← CLI principal
├── requirements.txt                ← dependência Python (pyyaml)
├── config/
│   └── cluster.yaml                ← ÚNICO arquivo que você edita
├── vagrant/
│   ├── Vagrantfile                 ← lê cluster.yaml e define as VMs
│   └── scripts/
│       ├── bootstrap-common.sh     ← executado em todos os nodes
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

# Versões dos addons instalados no cluster
addons:
  calico:
    version: "3.30.2"

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
    - name: wk-3
      cpus: 2
      memory_mb: 3072
    - name: wk-4
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
python cka-lab.py validate-network
```

Saída esperada:

```
[info] Interfaces de rede disponíveis no host:

Name       InterfaceDescription                        Status  LinkSpeed
----       --------------------                        ------  ---------
Ethernet   Intel(R) Ethernet Connection (2) I219-V     Up      1 Gbps
Wi-Fi      Qualcomm Atheros AR938x Wireless Adapter    Disconnected  0 bps

[info] Interface configurada em cluster.yaml: 'Intel(R) Ethernet Connection'
[warn] Ajuste network.bridge_interface com o nome exato da interface desejada.
```

Copie o valor da coluna **Name** da interface com status **Up** e cole exatamente em `config/cluster.yaml`:

```yaml
network:
  bridge_interface: "Intel(R) Ethernet Connection (2) I219-V"
```

### 4. Subir o cluster

```bash
python cka-lab.py up
```

O script verifica os pré-requisitos automaticamente antes de subir qualquer VM:

```
[info] Verificando pré-requisitos...

[ok] Vagrant 2.4.9
[ok] VirtualBox (VBoxManage) 7.2.6
[ok] config/cluster.yaml encontrado
[ok] Vagrantfile encontrado
[ok] RAM: 32684 MB total, cluster requer ~16384 MB

[ok] Todos os pré-requisitos OK.

[info] Estado atual das VMs:
[warn]   cp-1: not_created
[warn]   wk-1: not_created
[warn]   wk-2: not_created
[warn]   wk-3: not_created
[warn]   wk-4: not_created

[info] VMs a iniciar: cp-1, wk-1, wk-2, wk-3, wk-4
```

> **Primeira execução:** o Vagrant baixa a box `bento/ubuntu-22.04` (~700 MB). Acontece só uma vez.

> **Pergunta sobre bridge:** se aparecer `Which interface should the network bridge to?`, digite `1` e Enter. Não acontece quando o nome da interface no `cluster.yaml` é exato.

O processo completo leva entre **15 e 30 minutos** dependendo da conexão e hardware.

### 5. Verificar o status das VMs

```bash
python cka-lab.py status
```

```
[info] Estado das VMs:

[ok]   cp-1: running
[ok]   wk-1: running
[ok]   wk-2: running
[ok]   wk-3: running
[ok]   wk-4: running
```

### 6. Exportar o kubeconfig

```bash
python cka-lab.py export-kubeconfig
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
- `~/.kube/config` — padrão do kubectl (merge automático, preserva outros clusters)

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
cka-certification-lab-wk-1   Ready    <none>          9m    v1.34.7
cka-certification-lab-wk-2   Ready    <none>          7m    v1.34.7
cka-certification-lab-wk-3   Ready    <none>          5m    v1.34.7
cka-certification-lab-wk-4   Ready    <none>          3m    v1.34.7
```

Cluster pronto para uso.

---

## Ciclo de vida do cluster

O projeto tem três comandos distintos para gerenciar o estado das VMs. Entenda a diferença:

| Comando | O que faz | VMs existem depois? | Dados preservados? |
|---|---|---|---|
| `python cka-lab.py up` | Cria e inicia as VMs | Sim | Sim |
| `python cka-lab.py down` | Desliga as VMs (halt) | Sim | Sim |
| `python cka-lab.py destroy` | Apaga as VMs permanentemente | Não | Não |

### Desligar o cluster (preserva tudo)

Use quando quiser liberar RAM e CPU do host sem perder o cluster:

```bash
python cka-lab.py down
```

```
[info] Desligando: cp-1, wk-1, wk-2, wk-3, wk-4
[info] Executando: vagrant halt
...
[ok] VMs desligadas. Os dados foram preservados.
[info] Para ligar novamente: python cka-lab.py up
```

### Ligar o cluster novamente

```bash
python cka-lab.py up
```

O script detecta automaticamente quais VMs estão desligadas (`poweroff`) e as liga sem re-provisionar — em segundos, sem reinstalar nada:

```
[info] Estado atual das VMs:
[warn]   cp-1: poweroff
[warn]   wk-1: poweroff
[warn]   wk-2: poweroff
[warn]   wk-3: poweroff
[warn]   wk-4: poweroff

[info] VMs a iniciar: cp-1, wk-1, wk-2, wk-3, wk-4
```

### Destruir o cluster (apaga tudo)

Use quando quiser começar do zero:

```bash
python cka-lab.py destroy --force
```

Para recriar depois:

```bash
python cka-lab.py up
python cka-lab.py export-kubeconfig
kubectl get nodes
```

---

## Referência dos comandos

```bash
# Verificar pré-requisitos e listar interfaces de rede
python cka-lab.py validate-network

# Subir o cluster (verifica pré-req, detecta VMs já criadas ou desligadas)
python cka-lab.py up

# Desligar as VMs sem destruir — preserva dados e configurações
python cka-lab.py down

# Ver estado atual de cada VM
python cka-lab.py status

# Exportar kubeconfig e fazer merge em ~/.kube/config
python cka-lab.py export-kubeconfig

# Destruir as VMs permanentemente (pede confirmação)
python cka-lab.py destroy

# Destruir sem confirmação
python cka-lab.py destroy --force

# Ajuda
python cka-lab.py --help
```

---

## Operações comuns

### Adicionar um worker

Edite `config/cluster.yaml` e acrescente uma entrada na lista:

```yaml
  workers:
    - name: wk-1
      cpus: 2
      memory_mb: 3072
    - name: wk-5        # ← novo
      cpus: 2
      memory_mb: 3072
```

```bash
python cka-lab.py up    # sobe só o wk-5, ignora os que já estão rodando
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

Digite `1` e Enter. Para não perguntar mais, coloque o nome **exato** no `cluster.yaml` incluindo o sufixo completo.

---

### VBoxManage não encontrado

```
[error] VirtualBox (VBoxManage) não encontrado — instale antes de continuar.
```

O `cka-lab.py` procura automaticamente em `C:\Program Files\Oracle\VirtualBox\`. Se ainda não encontrar, adicione ao PATH:

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
python cka-lab.py export-kubeconfig
```

O `cka-lab.py` corrige o endereço automaticamente para `192.168.99.10`.

---

### Erro de certificado TLS após recriar o cluster

```
tls: failed to verify certificate: x509: certificate signed by unknown authority
```

O kubeconfig tem o certificado do cluster antigo. Rode:

```bash
python cka-lab.py export-kubeconfig
```

O merge sobrescreve a entrada existente com os novos certificados.

---

### Ctrl+C não para a execução

O Ctrl+C encerra o Vagrant corretamente. Se o terminal travar mesmo assim, abra outro terminal e rode:

```bash
python cka-lab.py down
```

---

## Simulador de exame — cenários práticos

O projeto inclui 20 cenários que simulam o formato real do CKA: o ambiente já está quebrado e você precisa diagnosticar e corrigir, com verificação automática da solução.

```bash
python cka-lab.py scenario list              # ver todos os cenários
python cka-lab.py scenario deploy 01         # implantar um cenário
python cka-lab.py scenario verify 01         # verificar sua solução
python cka-lab.py scenario hint   01         # ver uma dica
python cka-lab.py scenario reset  01         # desfazer o cenário
```

Guia completo de uso, catálogo e ordem de estudo: [SCENARIOS.md](SCENARIOS.md)

---

## Labs de estudo CKA

Os labs cobrem todos os domínios do exame com exercícios práticos aplicados diretamente no cluster.

| Arquivo | Domínio | Peso |
|---|---|---|
| [`labs/01-cluster-architecture.md`](labs/01-cluster-architecture.md) | Cluster Architecture, Installation & Configuration | 25% |
| [`labs/02-workloads-scheduling.md`](labs/02-workloads-scheduling.md) | Workloads & Scheduling | 15% |
| [`labs/03-services-networking.md`](labs/03-services-networking.md) | Services & Networking | 20% |
| [`labs/04-storage.md`](labs/04-storage.md) | Storage | 10% |
| [`labs/05-troubleshooting.md`](labs/05-troubleshooting.md) | Troubleshooting | 30% |

Para o currículo completo do exame com datas e pesos: [`cka-curriculum.md`](cka-curriculum.md)

---

## Roadmap

**Concluído**
- [x] Configuração central em `cluster.yaml` (versões, nomes e recursos por node)
- [x] Vagrantfile dinâmico que lê a lista de nodes do YAML
- [x] Bootstrap via shell scripts (containerd + kubeadm + Calico)
- [x] Versão do Calico configurável no `cluster.yaml`
- [x] CLI Python com validação de pré-requisitos (Vagrant, VirtualBox, RAM)
- [x] Detecção de estado das VMs — retoma sem recriar o que já existe
- [x] Ctrl+C funcional — encerra o Vagrant corretamente no Windows
- [x] Rede host-only com IPs estáticos (sem conflito de DHCP)
- [x] Comando `down` para desligar sem destruir
- [x] Export do kubeconfig com merge automático em `~/.kube/config`
- [x] Correção automática do IP e certificado no kubeconfig exportado
- [x] Labs de estudo para todos os domínios CKA (labs/01 a 05)
- [x] Currículo oficial do exame documentado (`cka-curriculum.md`)

**Planejado**
- [ ] Export automático do kubeconfig ao final do `up`
- [ ] Detecção automática da interface bridge
- [ ] Ingress controller opcional (nginx) pré-instalado
- [ ] HA com 3 control planes
- [ ] Suporte a Linux host
