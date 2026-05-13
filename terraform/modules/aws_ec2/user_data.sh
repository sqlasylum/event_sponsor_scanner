#!/bin/bash
set -euo pipefail

# Install Docker from official Docker repository
apt-get update -y
apt-get install -y ca-certificates curl git

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable --now docker
usermod -aG docker ubuntu

# Clone the repo
git clone ${repo_url} /opt/app
cd /opt/app

# Write env file
cat > .env <<'ENVEOF'
DATABASE_URL=postgresql+asyncpg://scanner:${db_password}@db:5432/scanner
DB_PASSWORD=${db_password}
SECRET_KEY=${secret_key}
ADMIN_PASSWORD=${admin_password}
EVENT_NAME=${event_name}
BASE_URL=${base_url}
ENVEOF

# Start services
docker compose up -d --build
