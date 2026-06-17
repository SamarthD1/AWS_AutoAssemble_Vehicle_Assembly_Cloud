# AWS EC2 Deployment Guide - AutoAssemble Cloud Portal

This guide provides step-by-step instructions for deploying the AutoAssemble Vehicle Assembly Cloud Portal onto a single AWS EC2 instance running either **Ubuntu Server** or **Amazon Linux 2023**.

---

## 🏗️ Step 1: Provision an AWS EC2 Instance

1. Log in to the [AWS Management Console](https://aws.amazon.com/console/).
2. Navigate to **EC2 Dashboard** and click **Launch Instance**.
3. **Application and OS Images (AMI)**:
   - **Option A (Ubuntu)**: Choose **Ubuntu Server 22.04 LTS** (or 24.04 LTS).
   - **Option B (Amazon Linux)**: Choose **Amazon Linux 2023 (AL2023)**.
4. **Instance Type**: Select **t2.micro** or **t3.micro** (Free Tier eligible).
5. **Key Pair**: Select an existing key pair or create a new one (e.g., `autoassemble-key.pem`).
6. **Network Settings (Security Group)**:
   - Create a security group.
   - Add the following inbound security group rules:
     - **SSH**: Port `22` (Source: `My IP` or `0.0.0.0/0` if necessary).
     - **HTTP**: Port `80` (Source: `0.0.0.0/0`) for web access.
     - **HTTPS** (Optional): Port `443` (Source: `0.0.0.0/0`) for SSL.
7. Launch the instance and note the **Public IPv4 Address**.

---

## 🔑 Step 2: Connect via SSH

Open a terminal on your host machine, navigate to your `.pem` key pair location, and run the SSH command matching your chosen OS:

### Option A: For Ubuntu LTS
```bash
chmod 400 autoassemble-key.pem
ssh -i autoassemble-key.pem ubuntu@<EC2-PUBLIC-IP>
```

### Option B: For Amazon Linux 2023
```bash
chmod 400 autoassemble-key.pem
ssh -i autoassemble-key.pem ec2-user@<EC2-PUBLIC-IP>
```

---

## 🐳 Step 3: Install Docker and Docker Compose on EC2

Choose the installation script corresponding to your operating system:

### Option A: For Ubuntu LTS (Debian-based)
```bash
# Update system packages
sudo apt-get update -y && sudo apt-get upgrade -y
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# Add Docker GPG Key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Register Docker Apt repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine and Compose plugin
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable service
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group (bypasses sudo)
sudo usermod -aG docker ubuntu

# Log out and reconnect to apply group permissions
exit
```

### Option B: For Amazon Linux 2023 (RHEL-based)
```bash
# Update packages
sudo dnf update -y

# Install Docker and Docker Compose CLI plugin
sudo dnf install -y docker docker-compose-plugin

# Start and enable service
sudo systemctl start docker
sudo systemctl enable docker

# Add ec2-user to docker group
sudo usermod -aG docker ec2-user

# Log out and reconnect to apply group permissions
exit
```

---

## 📂 Step 4: Deploy application codebase to EC2

SSH back into your instance. Clone or copy your code to the instance root:

```bash
# Reconnect to instance:
# ssh -i autoassemble-key.pem ubuntu@<EC2-PUBLIC-IP>    (for Ubuntu)
# ssh -i autoassemble-key.pem ec2-user@<EC2-PUBLIC-IP>  (for Amazon Linux)

git clone <YOUR_GIT_REPOSITORY_URL> autoassemble
cd autoassemble
```

---

## ⚡ Step 5: Start the Application

Build and start the multi-container stack in detached mode:

```bash
docker compose up -d --build
```
This launches:
- `auto_assemble_db`: Built from `db.Dockerfile` (preloaded with `database.sql` schemas and test data).
- `auto_assemble_web`: Running Flask + Gunicorn, mapped to public port 80.

Check container states and service health:
```bash
docker compose ps
```

---

## 🔎 Step 6: Verify Access

Open a web browser and visit:
`http://<EC2-PUBLIC-IP>`

Log in using the primary seed records:
- **Administrator**: `admin` / `admin123`
- **Production Manager**: `manager` / `manager123`
- **Operations Staff**: `staff` / `staff123`

To inspect logs:
```bash
docker compose logs -f web
docker compose logs -f db
```

---

## 🔒 Step 7: (Recommended) Configure SSL & Reverse Proxy

To secure production deployments on port 443 with Nginx and Let's Encrypt SSL:

### 1. Bind Flask Locally
Modify `docker-compose.yml` to bind web ports to `127.0.0.1:5000:5000` (instead of `80:5000`) so that external traffic is forced through the Nginx reverse proxy.

### 2. Install Nginx and Certbot

#### On Ubuntu LTS
```bash
sudo apt-get install -y nginx certbot python3-certbot-nginx
```

#### On Amazon Linux 2023
```bash
sudo dnf install -y nginx python3-pip
sudo python3 -m venv /opt/certbot/
sudo /opt/certbot/bin/pip install --upgrade pip
sudo /opt/certbot/bin/pip install certbot certbot-nginx
sudo ln -s /opt/certbot/bin/certbot /usr/bin/certbot
sudo systemctl enable nginx
sudo systemctl start nginx
```

### 3. Create Nginx Configuration Block

#### On Ubuntu LTS
Create `/etc/nginx/sites-available/autoassemble`:
```nginx
server {
    listen 80;
    server_name yourdomain.com; # Replace with your domain

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
Link the file and restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/autoassemble /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo systemctl restart nginx
```

#### On Amazon Linux 2023
Create `/etc/nginx/conf.d/autoassemble.conf`:
```nginx
server {
    listen 80;
    server_name yourdomain.com; # Replace with your domain

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
Restart Nginx:
```bash
sudo systemctl restart nginx
```

### 4. Fetch Let's Encrypt Certificate
Verify that your domain DNS record points to your EC2 public IP. Run:
```bash
sudo certbot --nginx -d yourdomain.com
```
Follow the interactive prompts to enable Let's Encrypt. The script will automatically upgrade port 80 to port 443 with secure SSL certificates.
