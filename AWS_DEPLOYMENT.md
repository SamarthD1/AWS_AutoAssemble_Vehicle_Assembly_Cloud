# AWS EC2 & RDS Deployment Guide - AutoAssemble Cloud Portal

This guide provides step-by-step instructions for deploying the AutoAssemble Vehicle Assembly Cloud Portal onto a single AWS EC2 instance running **Amazon Linux 2023** and connecting it to a managed **Amazon RDS MySQL 8.4** instance.

---

## 🏗️ Step 1: Provision your AWS VPC Infrastructure

1. **VPC Configuration**:
   - Create a Custom VPC named `AutoAssemble-VPC` with CIDR block `10.0.0.0/16`.
2. **Subnets Configuration**:
   - **Public Subnet 1**: Name `Public-Subnet` (CIDR: `10.0.1.0/24`) in Availability Zone A (used for EC2 deployment).
   - **Public Subnet 2**: Name `Public-Subnet-2` (CIDR: `10.0.2.0/24`) in Availability Zone B (needed for RDS Subnet Group Multi-AZ configuration).
3. **Internet Gateway**:
   - Create `AutoAssemble-IGW` and attach it to your VPC.
4. **Route Table**:
   - Create `AutoAssemble-RT`.
   - Add a route: Destination `0.0.0.0/0` ──► Target `AutoAssemble-IGW`.
   - Associate this route table with both subnets.

---

## 🔒 Step 2: Configure Security Groups

1. **EC2 Security Group (`AutoAssemble-SG`)**:
   - Allow **SSH** (Port 22) from your IP or anywhere.
   - Allow **HTTP** (Port 80) from anywhere (`0.0.0.0/0`).
   - Allow **Flask** (Port 5000) from anywhere.
2. **RDS Security Group (`autoassemble-rds-sg`)**:
   - Allow **MYSQL/Aurora** (Port 3306) from the source VPC CIDR **`10.0.0.0/16`** (restricts database access only to instances inside the VPC).

---

## 🐧 Step 3: EC2 and Linux Administration Setup

Launch a `t2.micro` EC2 instance using **Amazon Linux 2023** and your key pair (`AutoAssemble-Key.pem`).

### 1. Connect via SSH
```bash
chmod 400 AutoAssemble-Key.pem
ssh -i AutoAssemble-Key.pem ec2-user@<EC2-PUBLIC-IP>
```

### 2. Configure Users and Permissions
Create the operations team accounts and group on your EC2 instance:
```bash
# Create users
sudo useradd admin
sudo useradd manager
sudo useradd operator

# Set passwords
sudo passwd admin
sudo passwd manager
sudo passwd operator

# Create the production group and add the users
sudo groupadd production
sudo usermod -aG production admin
sudo usermod -aG production manager
sudo usermod -aG production operator
```

### 3. Install and Configure Docker
```bash
# Update repositories
sudo dnf update -y

# Install Docker
sudo dnf install docker -y

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Allow ec2-user to run docker commands without sudo
sudo usermod -aG docker ec2-user

# Log out and reconnect to refresh group permissions
exit
```

Log back in:
```bash
ssh -i AutoAssemble-Key.pem ec2-user@<EC2-PUBLIC-IP>
```

---

## 🗄️ Step 4: Import Database Schema to Amazon RDS

Ensure your RDS instance is created with **MySQL 8.4** inside your VPC subnet group and is active at endpoint:
`database-1.cv44ak4uaxvi.ap-south-1.rds.amazonaws.com`

### 1. Install MySQL Client on EC2
```bash
sudo dnf install mariadb105 -y  # Installs mysql client CLI utility
```

### 2. Import schema and seed data
Run the schema import by connecting to the RDS server:
```bash
mysql -h database-1.cv44ak4uaxvi.ap-south-1.rds.amazonaws.com -u admin -p < database.sql
```
*(Enter your RDS master password when prompted. This creates the `auto_assemble_db` database and imports seed records).*

---

## 🐳 Step 5: Build & Run the Application Container

### 1. Clone the project code
```bash
git clone https://github.com/SamarthD1/AWS_AutoAssemble_Vehicle_Assembly_Cloud.git
cd AWS_AutoAssemble_Vehicle_Assembly_Cloud
```

### 2. Build the Docker Image
```bash
docker build -t autoassemble .
```

### 3. Start the application container
Run the container on port 80 and inject the Amazon RDS environment variables to avoid the `Database connection pool is not initialized` error:

```bash
docker run -d \
  -p 80:5000 \
  --name autoassemble-app \
  -e DB_HOST=database-1.cv44ak4uaxvi.ap-south-1.rds.amazonaws.com \
  -e DB_USER=admin \
  -e DB_PASSWORD=<YOUR_RDS_PASSWORD> \
  -e DB_NAME=auto_assemble_db \
  -e DB_PORT=3306 \
  -e FLASK_SECRET_KEY="production-secret-key" \
  autoassemble
```
*(Replace `<YOUR_RDS_PASSWORD>` with your actual AWS RDS master password).*

---

## 🔎 Step 6: Verify Deployment

1. Check if the container is running successfully:
   ```bash
   docker ps
   ```
2. Check the container application logs:
   ```bash
   docker logs autoassemble-app
   ```
3. Open a browser and navigate to:
   `http://<EC2-PUBLIC-IP>`
   
4. Log in using the default portal credentials:
   - **Administrator**: `admin` / `admin123`
   - **Production Manager**: `manager` / `manager123`
   - **Operations Staff**: `staff` / `staff123`
