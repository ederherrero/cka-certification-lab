#!/usr/bin/env bash
set -euo pipefail

HOST_ONLY_BASE="${HOST_ONLY_BASE:-192.168.99}"
CLUSTER_NAME="${CLUSTER_NAME:-cka-lab}"
API_IP="${HOST_ONLY_BASE}.10"
APP_DIR="/opt/cka-lab"
SERVICE_NAME="cka-lab"

echo "[manager] Instalando dependências..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv curl openssh-client git

echo "[manager] Instalando kubectl..."
curl -fsSL "https://pkgs.k8s.io/core:/stable:/v1.34/deb/Release.key" \
  | gpg --batch --yes --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] \
  https://pkgs.k8s.io/core:/stable:/v1.34/deb/ /" \
  > /etc/apt/sources.list.d/kubernetes.list
apt-get update -qq
apt-get install -y -qq kubectl
apt-mark hold kubectl

echo "[manager] Instalando ttyd (terminal web)..."
systemctl stop cka-terminal 2>/dev/null || true
curl -fsSL https://github.com/tsl0922/ttyd/releases/latest/download/ttyd.x86_64 \
  -o /usr/local/bin/ttyd
chmod +x /usr/local/bin/ttyd

echo "[manager] Aguardando API do Kubernetes em ${API_IP}:6443..."
for i in $(seq 1 60); do
  if curl -sk "https://${API_IP}:6443/healthz" | grep -q "ok"; then
    echo "[manager] API disponível."
    break
  fi
  echo "[manager] Aguardando... (${i}/60)"
  sleep 10
done

echo "[manager] Aguardando kubeconfig do control plane..."
for i in $(seq 1 30); do
  if [[ -f /vagrant/shared/admin.conf ]]; then
    echo "[manager] kubeconfig encontrado."
    break
  fi
  sleep 10
done

echo "[manager] Configurando kubectl..."
mkdir -p /home/vagrant/.kube /root/.kube
cp /vagrant/shared/admin.conf /home/vagrant/.kube/config
cp /vagrant/shared/admin.conf /root/.kube/config
chown vagrant:vagrant /home/vagrant/.kube/config

echo "[manager] Configurando chave SSH para acesso aos nodes..."
mkdir -p /home/vagrant/.ssh
curl -fsSL https://raw.githubusercontent.com/hashicorp/vagrant/main/keys/vagrant \
  -o /home/vagrant/.ssh/lab_key
chmod 600 /home/vagrant/.ssh/lab_key
chown vagrant:vagrant /home/vagrant/.ssh/lab_key

for i in 10 11 12 13; do
  ssh-keyscan -H "${HOST_ONLY_BASE}.${i}" >> /home/vagrant/.ssh/known_hosts 2>/dev/null || true
done
chown vagrant:vagrant /home/vagrant/.ssh/known_hosts

echo "[manager] Criando SSH config para acesso por nome aos nodes..."
cat > /home/vagrant/.ssh/config <<EOF
Host cp-1
  HostName ${HOST_ONLY_BASE}.10
  User vagrant
  IdentityFile ~/.ssh/lab_key
  StrictHostKeyChecking no

Host wk-1
  HostName ${HOST_ONLY_BASE}.11
  User vagrant
  IdentityFile ~/.ssh/lab_key
  StrictHostKeyChecking no

Host wk-2
  HostName ${HOST_ONLY_BASE}.12
  User vagrant
  IdentityFile ~/.ssh/lab_key
  StrictHostKeyChecking no

Host wk-3
  HostName ${HOST_ONLY_BASE}.13
  User vagrant
  IdentityFile ~/.ssh/lab_key
  StrictHostKeyChecking no
EOF
chmod 600 /home/vagrant/.ssh/config
chown vagrant:vagrant /home/vagrant/.ssh/config

echo "[manager] Criando perfil do terminal interativo..."
cat > /home/vagrant/.ttyd_profile <<PROFILE
export KUBECONFIG=/home/vagrant/.kube/config
export PS1='\[\033[01;36m\]cka-lab\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
alias k=kubectl
alias kgn='kubectl get nodes'
alias kgp='kubectl get pods -A'

clear
printf '\033[1;36m'
echo '╔══════════════════════════════════════════════════════════╗'
echo '║   CKA Lab — Terminal Interativo                          ║'
echo '╠══════════════════════════════════════════════════════════╣'
echo '║  kubectl:   k  kgn  kgp                                  ║'
echo '║                                                          ║'
echo '║  SSH nos nodes (sem IP, sem senha):                      ║'
echo '║    ssh cp-1   ssh wk-1   ssh wk-2   ssh wk-3             ║'
echo '║                                                          ║'
echo '║  Aliases úteis:                                          ║'
echo '║    k         → kubectl                                   ║'
echo '║    kgn       → kubectl get nodes                         ║'
echo '║    kgp       → kubectl get pods -A                       ║'
echo '║                                                          ║'
echo '║  Conectar nos nodes via SSH:                             ║'
printf "║    ssh-cp1   → cp-1   (%s.10)                    ║\n" "${HOST_ONLY_BASE}"
printf "║    ssh-wk1   → wk-1   (%s.11)                    ║\n" "${HOST_ONLY_BASE}"
printf "║    ssh-wk2   → wk-2   (%s.12)                    ║\n" "${HOST_ONLY_BASE}"
printf "║    ssh-wk3   → wk-3   (%s.13)                    ║\n" "${HOST_ONLY_BASE}"
echo '║                                                          ║'
echo '║  Ou diretamente:                                         ║'
printf "║    ssh -i ~/.ssh/lab_key vagrant@%s.<N>          ║\n" "${HOST_ONLY_BASE}"
echo '╚══════════════════════════════════════════════════════════╝'
printf '\033[0m\n'
kubectl get nodes
echo ''
PROFILE
chown vagrant:vagrant /home/vagrant/.ttyd_profile

echo "[manager] Instalando o web app..."
mkdir -p "${APP_DIR}"
cp -r /vagrant/app/. "${APP_DIR}/"
mkdir -p "${APP_DIR}/config"
cp /vagrant/config/cluster.yaml "${APP_DIR}/config/cluster.yaml"

python3 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/pip" install --quiet -r "${APP_DIR}/requirements.txt"

echo "[manager] Criando arquivo de configuração do app..."
cat > "${APP_DIR}/.env" <<EOF
HOST_ONLY_BASE=${HOST_ONLY_BASE}
SSH_KEY=/home/vagrant/.ssh/lab_key
SSH_USER=vagrant
KUBECONFIG=/home/vagrant/.kube/config
PROGRESS_FILE=/var/lib/cka-lab/progress.json
EOF

mkdir -p /var/lib/cka-lab
chown vagrant:vagrant /var/lib/cka-lab

echo "[manager] Criando serviço systemd do web app..."
cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=CKA Lab Web App
After=network.target

[Service]
Type=simple
User=vagrant
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
Environment=KUBECONFIG=/home/vagrant/.kube/config
ExecStart=${APP_DIR}/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "[manager] Criando serviço systemd do terminal (ttyd)..."
cat > "/etc/systemd/system/cka-terminal.service" <<EOF
[Unit]
Description=CKA Lab Terminal (ttyd)
After=network.target

[Service]
Type=simple
User=vagrant
Environment=KUBECONFIG=/home/vagrant/.kube/config
Environment=HOME=/home/vagrant
ExecStart=/usr/local/bin/ttyd --port 7681 --writable --max-clients 5 bash --rcfile /home/vagrant/.ttyd_profile
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}" cka-terminal
systemctl start "${SERVICE_NAME}" cka-terminal

echo "[manager] Web app disponível em http://localhost:8080"
echo "[manager] Terminal disponível em http://localhost:7681"
echo "[manager] Concluído."
