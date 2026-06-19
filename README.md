# AutoAssemble: Vehicle Assembly Cloud Portal

AutoAssemble is a cloud-native, enterprise-grade automotive manufacturing and assembly management portal. This project is built and deployed as a demonstration of cloud engineering, Linux administration, containerized microservices, security protocols, and database management on Amazon Web Services (AWS).

## 📄 Project Documentation

For full project requirements, architectural diagrams, and references, please view the [Google Document](https://docs.google.com/document/d/1eVY2Fit-_wNz6y82lluuRC_P6mPuux-T7gI_cD32Vfg/edit?usp=sharing).

---

## 🏗️ Project Architecture

```
User Browser
    │
    ▼ (Port 80 HTTP)
AWS Custom VPC (10.0.0.0/16) ──► Public Subnet (10.0.1.0/24)
                                         │
                                         ▼
                                   AWS EC2 Instance (Amazon Linux 2023)
                                         │
                                         ▼
                                   Docker Container (Flask App)
                                         │
                                         ▼
                                   Amazon RDS MySQL 8.4 (database-1.cv44ak4uaxvi.ap-south-1.rds.amazonaws.com)
```

---

## 🌐 AWS Infrastructure Setup

### Region
- **`ap-south-1`** (Mumbai)

### Networking (VPC & Subnets)
- **VPC**: `AutoAssemble-VPC` (CIDR: `10.0.0.0/16`)
- **Subnets**:
  - `Public-Subnet` (CIDR: `10.0.1.0/24`) — Used for EC2 Instance deployment.
  - `Public-Subnet-2` (CIDR: `10.0.2.0/24`) — Used for RDS Multi-AZ support.
- **Internet Gateway**: `AutoAssemble-IGW` attached to `AutoAssemble-VPC`.
- **Route Table**: `AutoAssemble-RT` associated with both subnets, routing `0.0.0.0/0` to the Internet Gateway (`AutoAssemble-IGW`).

### Security Groups
1. **EC2 Security Group (`AutoAssemble-SG`)**:
   - Inbound SSH (Port 22): Source `0.0.0.0/0` (or restricted to your IP).
   - Inbound HTTP (Port 80): Source `0.0.0.0/0`.
   - Inbound Flask (Port 5000): Source `0.0.0.0/0`.
2. **RDS Security Group (`autoassemble-rds-sg`)**:
   - Inbound MySQL (Port 3306): Source `10.0.0.0/16` (restricts database access only to instances running inside the custom VPC).

---

## 🐧 Linux Administration on EC2

The application is deployed on an **Amazon Linux 2023** EC2 Instance (`t2.micro`).

### SSH Connection (macOS / Linux)
```bash
chmod 400 AutoAssemble-Key.pem
ssh -i AutoAssemble-Key.pem ec2-user@<EC2_PUBLIC_IP>
```

### User, Group, and Permission Configuration
To set up access controls for the manufacturing operations team, we configure users, groups, and standard permissions:

```bash
# 1. Create system users
sudo useradd admin
sudo useradd manager
sudo useradd operator

# 2. Assign secure passwords
sudo passwd admin
sudo passwd manager
sudo passwd operator

# 3. Establish the production group and append the users
sudo groupadd production
sudo usermod -aG production admin
sudo usermod -aG production manager
sudo usermod -aG production operator
```

### Installing Docker on Amazon Linux 2023
```bash
# Update repositories
sudo dnf update -y

# Install Docker
sudo dnf install docker -y

# Start and enable the service
sudo systemctl start docker
sudo systemctl enable docker

# Allow ec2-user to execute docker commands without sudo
sudo usermod -aG docker ec2-user

# Log out and reconnect to apply group permissions
exit
```

---

## 🗄️ Amazon RDS Database Setup

- **Database Engine**: MySQL Community Edition (Version `8.4`)
- **RDS Endpoint**: `database-1.cv44ak4uaxvi.ap-south-1.rds.amazonaws.com`
- **Default Database Name**: `autoassemble`
- **Actual Imported Schema Database**: `auto_assemble_db` (Specified inside `database.sql`)

### Verify Connection From EC2:
```bash
mysql -h database-1.cv44ak4uaxvi.ap-south-1.rds.amazonaws.com -u admin -p
```

### Import the Database Schema:
```bash
mysql -h database-1.cv44ak4uaxvi.ap-south-1.rds.amazonaws.com -u admin -p < database.sql
```
*Note: This creates the tables: `roles`, `users`, `vehicles`, `production_orders`, `employees`, `tasks`, `reports`, and `activity_logs`.*

---

## 🔍 Connection Troubleshooting & Root Cause Analysis

### Problem Encountered
When deploying the container, the application failed to start and threw the error:
`Database connection pool is not initialized`

### Root Cause Analysis
By default, the application's config was set to connect to a local MySQL container for local development:
```python
DB_HOST = "db"
DB_USER = "auto_user"
DB_PASSWORD = "auto_pass123"
DB_NAME = "auto_assemble_db"
```
Because the EC2 deployment targets an external **Amazon RDS** endpoint (`database-1.cv44ak4uaxvi.ap-south-1.rds.amazonaws.com`), the application was looking for a server named `db` on the local network, which does not exist, causing the connector pool initialization to fail.

### Solution
Flask's `config.py` was designed to check for environment variables first. We resolve the connection pool failure by passing the RDS connection variables into the Docker container runtime using the `-e` flag.

---

## 🚀 Building & Running the Docker Container

### 1. Clone the Repository
```bash
git clone https://github.com/SamarthD1/AWS_AutoAssemble_Vehicle_Assembly_Cloud.git
cd AWS_AutoAssemble_Vehicle_Assembly_Cloud
```

### 2. Build the Docker Image
```bash
docker build -t autoassemble .
```

### 3. Run the Container using RDS Variables
Run the container on port 80 and inject the Amazon RDS database connection settings:

```bash
docker run -d \
  -p 80:5000 \
  --name autoassemble-app \
  -e DB_HOST=database-1.cv44ak4uaxvi.ap-south-1.rds.amazonaws.com \
  -e DB_USER=admin \
  -e DB_PASSWORD=<RDS_PASSWORD> \
  -e DB_NAME=auto_assemble_db \
  -e DB_PORT=3306 \
  -e FLASK_SECRET_KEY="production-session-secret" \
  autoassemble
```
*(Replace `<RDS_PASSWORD>` with your actual AWS RDS master password).*

---

## 🛠️ Frequently Used Commands

### Check Container Status
```bash
docker ps -a
```

### View Application Logs
```bash
docker logs autoassemble-app
```

### Inspect Database Tables
```bash
mysql -h database-1.cv44ak4uaxvi.ap-south-1.rds.amazonaws.com -u admin -p

# Inside MySQL prompt:
USE auto_assemble_db;
SHOW TABLES;
```

---

## 🔑 Default Portal Accounts
Once the container starts, open your browser at `http://<EC2-PUBLIC-IP>` and sign in with:

| Role | Username | Password |
| :--- | :--- | :--- |
| **Administrator** | `admin` | `admin123` |
| **Production Manager** | `manager` | `manager123` |
| **Operations Staff** | `staff` | `staff123` |
