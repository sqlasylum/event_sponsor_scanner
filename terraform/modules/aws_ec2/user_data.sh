#!/bin/bash
set -euo pipefail

# Install Docker
apt-get update -y
apt-get install -y docker.io docker-compose-plugin git

systemctl enable --now docker
usermod -aG docker ubuntu

# Clone the repo
git clone https://github.com/your-org/event_sponsor_scanner.git /opt/app
cd /opt/app

# Write env file
cat > .env <<'ENVEOF'
DATABASE_URL=${database_url}
SECRET_KEY=${secret_key}
BASE_URL=${base_url}
ADMIN_TOKEN=${admin_token}
ENVEOF

# Start services
docker compose up -d --build
