#!/bin/bash
# AutoAssemble Application Deployment Automation Script
# Targets: Amazon Linux 2023 / RHEL-based cloud environments

set -e

# Configuration
REPO_URL="https://github.com/SamarthD1/AWS_AutoAssemble_Vehicle_Assembly_Cloud.git"
APP_DIR="/home/ec2-user/autoassemble"
DB_HOST="database-1.cv44ak4uaxvi.ap-south-1.rds.amazonaws.com"
DB_USER="admin"
DB_NAME="auto_assemble_db"
DB_PORT="3306"

echo "=========================================================="
echo "Starting AutoAssemble Cloud VM Deployment..."
echo "=========================================================="

# 1. Update OS package managers
echo "[1/6] Updating system repositories..."
sudo dnf update -y

# 2. Check and install Docker if missing
if ! command -v docker &> /dev/null; then
    echo "[2/6] Docker not found. Installing Docker Engine..."
    sudo dnf install docker -y
    sudo systemctl start docker
    sudo systemctl enable docker
    # Add active user to Docker group
    sudo usermod -aG docker $USER
    echo "Docker installed and enabled successfully."
else
    echo "[2/6] Docker already installed. Skipping."
fi

# 3. Configure system users and groups for administration
echo "[3/6] Configuring system administration accounts..."
for user in admin manager operator; do
    if ! id "$user" &>/dev/null; then
        sudo useradd "$user"
        # Set a default secure password (user should change this on first login)
        echo "$user:AutoAssemblePass2026!" | sudo chpasswd
        echo "Created system user: $user"
    fi
done

# Create production group if it doesn't exist
if ! getent group production >/dev/null; then
    sudo groupadd production
    sudo usermod -aG production admin
    sudo usermod -aG production manager
    sudo usermod -aG production operator
    echo "Configured 'production' group access controls."
fi

# 4. Clone or update repository codebase
echo "[4/6] Retrieving application files from Git..."
if [ -d "$APP_DIR" ]; then
    echo "Directory exists. Updating codebase..."
    cd "$APP_DIR"
    git pull
else
    echo "Cloning repository..."
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi

# 5. Build application container
echo "[5/6] Building Docker image 'autoassemble'..."
docker build -t autoassemble .

# 6. Stop and remove existing running instance
echo "[6/6] Launching new application instance..."
if docker ps -a --format '{{.Names}}' | grep -Eq "^autoassemble-app$"; then
    echo "Stopping existing autoassemble-app container..."
    docker stop autoassemble-app || true
    docker rm autoassemble-app || true
fi

# Prompt for the RDS database password
read -sp "Enter Amazon RDS Database Master Password: " RDS_PASS
echo ""

if [ -z "$RDS_PASS" ]; then
    echo "ERROR: RDS Database password cannot be empty. Aborting." >&2
    exit 1
fi

# Start the docker container with RDS environment variables
docker run -d \
  -p 80:5000 \
  --name autoassemble-app \
  --restart always \
  -e DB_HOST="$DB_HOST" \
  -e DB_USER="$DB_USER" \
  -e DB_PASSWORD="$RDS_PASS" \
  -e DB_NAME="$DB_NAME" \
  -e DB_PORT="$DB_PORT" \
  -e FLASK_SECRET_KEY="auto-assemble-production-secret" \
  autoassemble

echo "=========================================================="
echo "Deployment Complete! Service is running."
echo "Access portal at: http://localhost (or EC2 Public IP)"
echo "=========================================================="
exit 0
