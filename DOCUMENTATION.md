# Project Documentation: AutoAssemble Vehicle Assembly Cloud Portal

This document provides a comprehensive technical overview of the cloud architecture, network design, Linux administration, database management, monitoring, application features, and cost estimations for the **AutoAssemble Vehicle Assembly Cloud Portal**.

---

## 📖 1. Executive Summary & Domain Context

### Industry
Automotive Manufacturing & Assembly

### Problem Statement
AutoAssemble is experiencing rapid operational growth. Historically, operations relied on manual workflows, spreadsheet trackers, disconnected logging, and isolated reports. This setup led to database fragmentation, scheduling delays, and lack of real-time monitoring.

### Objective
This project establishes a centralized, highly available, secure, and monitorable cloud platform. It integrates shop-floor tracking, employee tasks, operational analytics, and security audits into a single deployment on Amazon Web Services (AWS) using containerized web applications (Docker) and managed relational databases (Amazon RDS).

---

## 🏗️ 2. Cloud Infrastructure & VPC Network Design

The network is deployed in the **ap-south-1** (Mumbai) AWS region, inside a custom-configured Virtual Private Cloud (VPC) to isolate compute resources from the public internet.

```
+-----------------------------------------------------------------------------+
| AWS Custom VPC: AutoAssemble-VPC (10.0.0.0/16)                             |
|                                                                             |
|  +-----------------------------+       +---------------------------------+  |
|  | Public-Subnet (10.0.1.0/24) |       | Public-Subnet-2 (10.0.2.0/24)   |  |
|  | (Availability Zone A)       |       | (Availability Zone B)           |  |
|  |                             |       |                                 |  |
|  |  +-----------------------+  |       |  +---------------------------+  |
|  |  |   Amazon EC2 VM       |  |       |  |  RDS Standby Instance     |  |
|  |  |  (Amazon Linux 2023)  |  |       |  |  (Multi-AZ Deployment)    |  |
|  |  |  [autoassemble-app]   |  |       |  +---------------------------+  |
|  |  +-----------┬-----------+  |       +---------------------------------+  |
|  +--------------┼--------------+                                              |
|                 │                                                           |
|                 │ (MySQL TCP 3306 - Restricted to 10.0.0.0/16)              |
|                 ▼                                                           |
|  +-----------------------------------------------------------------------+  |
|  | Amazon RDS MySQL 8.4 Primary: database-1 (AZ A)                       |  |
|  +-----------------------------------------------------------------------+  |
|                                                                             |
|  Internet Gateway (AutoAssemble-IGW) <──► Route Table (AutoAssemble-RT)    |
+-----------------------------------------------------------------------------+
```

### Network Configurations
- **Virtual Private Cloud (VPC)**: `AutoAssemble-VPC` (CIDR: `10.0.0.0/16`)
- **Subnets**:
  - `Public-Subnet`: `10.0.1.0/24` (Availability Zone `ap-south-1a`, maps EC2 host)
  - `Public-Subnet-2`: `10.0.2.0/24` (Availability Zone `ap-south-1b`, provides the secondary subnet for the Amazon RDS subnet group to satisfy Multi-AZ deployment constraints)
- **Internet Gateway (IGW)**: `AutoAssemble-IGW` attached to the VPC.
- **Route Table**: `AutoAssemble-RT` associated with both subnets, featuring a default route pointing `0.0.0.0/0` to `AutoAssemble-IGW`.

### Security Group Firewall Configurations
1. **EC2 Instance SG (`AutoAssemble-SG`)**:
   - Port 22 (SSH) Inbound: Allow admin configuration access.
   - Port 80 (HTTP) Inbound: Allow public web browser access.
   - Port 5000 (Flask) Inbound: Allow direct development testing.
2. **RDS Database SG (`autoassemble-rds-sg`)**:
   - Port 3306 (MySQL) Inbound: Restricted strictly to the VPC CIDR block **`10.0.0.0/16`**. This prevents direct database access from the public internet while allowing the EC2 host within the VPC to communicate with the DB.

---

## 🐧 3. Linux Administration & VM Deployment

The application is deployed on a virtual machine (EC2 instance) running **Amazon Linux 2023** (AL2023).

### User and Group Management
For secure server administration, specific user accounts are set up and added to a shared group `production` to control directory read/write privileges:
```bash
# Add users
sudo useradd admin
sudo useradd manager
sudo useradd operator

# Set passwords
sudo passwd admin
sudo passwd manager
sudo passwd operator

# Setup group and append users
sudo groupadd production
sudo usermod -aG production admin
sudo usermod -aG production manager
sudo usermod -aG production operator
```

### Docker Service Configuration
The application runs as a container managed by Docker. Docker was installed and enabled via the standard systemctl manager:
```bash
sudo dnf update -y
sudo dnf install docker -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user
```

---

## 🗄️ 4. Cloud Database Design & Troubleshooting

### Relational Database
- **Engine**: Amazon RDS MySQL Community Edition (Version `8.4`)
- **Database Endpoint**: `database-1.cv44ak4uaxvi.ap-south-1.rds.amazonaws.com`
- **Port**: `3306`

### Schema Design (`database.sql`)
The imported relational schema consists of:
- `roles`: RBAC roles list (`Administrator`, `Production Manager`, `Operations Staff`).
- `users`: Hashed login credentials linked to their roles.
- `vehicles`: Production records tracking vehicle type, model, assembly line, and overall completion date.
- `production_orders`: Tracking IDs, progress percentages, estimated completion dates, and status.
- `employees`: Active manufacturing plant staff directory.
- `tasks`: Active assignments mapped to employees with status states.
- `reports`: Saved report summaries.
- `activity_logs`: Logs tracking actions, logins, database changes, and access violations.

### 🛠️ Connection Pool Troubleshooting & Root Cause Analysis
During initial server deployment, the Docker container exited immediately with the error:
`Database connection pool is not initialized`

**Root Cause**: The application config (`config.py`) default values pointed to `db_host = "db"`, which is appropriate for a local Docker Compose setup but fails when connecting to external Amazon RDS. 

**Resolution**: Flask's `config.py` was updated to read from environment variables. We run the Docker container by injecting the variables using the `-e` runtime parameters, resolving the host address:
```bash
docker run -d \
  -p 80:5000 \
  --name autoassemble-app \
  -e DB_HOST=database-1.cv44ak4uaxvi.ap-south-1.rds.amazonaws.com \
  -e DB_USER=admin \
  -e DB_PASSWORD=<RDS_PASSWORD> \
  -e DB_NAME=auto_assemble_db \
  -e DB_PORT=3306 \
  -e FLASK_SECRET_KEY="production-secret" \
  autoassemble
```

---

## ⚙️ 5. Automation Scripts

Two shell scripts are located in the [scripts/](file:///Users/samarthdevadiga/Desktop/AWS_FINAL_Project/scripts) folder to automate operations:

1. **Backup Automation** ([backup.sh](file:///Users/samarthdevadiga/Desktop/AWS_FINAL_Project/scripts/backup.sh)):
   - Generates daily compressed database dumps using `mysqldump` against the RDS host.
   - Names files dynamically using timestamps.
   - Rotates backups, deleting files older than 7 days to conserve disk space.
2. **Server Deployment** ([deploy.sh](file:///Users/samarthdevadiga/Desktop/AWS_FINAL_Project/scripts/deploy.sh)):
   - Checks system dependencies and installs Docker if missing.
   - Configures the `admin`, `manager`, and `operator` system users and setup the group.
   - Pulls the latest code from GitHub.
   - Builds the Docker image and runs the container with the injected RDS credentials.

---

## 📊 6. Monitoring & Resource Management

System health and reliability are tracked using AWS CloudWatch and container logging:
1. **EC2 CPU & Memory Utilization**: Tracked via CloudWatch alarms. If CPU utilization exceeds 80% for 5 minutes, an alarm triggers to scale compute resources.
2. **Application Auditing & Logs**: Gunicorn writes logs to stdout/stderr. These logs can be viewed at any time using:
   ```bash
   docker logs -f autoassemble-app
   ```
3. **Database Health**: Measured via Amazon RDS metrics, tracking Read/Write IOPS, Free Storage Space, and Database Connections.
4. **Activity Logs Table**: Changes to vehicles, user logins, and unauthorized access attempts are logged directly to the database `activity_logs` table for compliance auditing.

---

## 🎨 7. Product Features & User Interfaces

The web application features a responsive Glassmorphic dashboard built using CSS Variables and Vanilla JavaScript.

- **Centralized Dashboard**: Renders live metrics for total/delayed vehicles, active employees, and assembly lines. Integrates theme-aware charts using **Chart.js** via CDN.
- **Role-Based Access Control (RBAC)**:
  - *Administrator*: Full access to all screens, including the security auditing log module.
  - *Production Manager*: Full CRUD on vehicles, orders, and employees, and views reports.
  - *Operations Staff*: Can view listings and update production tracking status and task progress.
- **Workflow & Automation**: Progress range inputs automatically calculate dates (e.g. marking progress as 100% updates vehicle status to `Completed` and records the current timestamp as the completion date).
- **Reports Section**: Formats vehicle counts, employee task loads, and line efficiencies, with direct **CSV exports**.

---

## 💰 8. AWS Cloud Infrastructure Pricing & Optimization Strategy

The infrastructure budget estimates are for the **ap-south-1 (Mumbai)** region.

### Monthly Pricing Breakdown (On-Demand)

| AWS Service | Resource Details | Usage Details | Monthly Cost (USD) |
| :--- | :--- | :--- | :--- |
| **AWS EC2** | 1 x `t3.micro` Instance (2 vCPUs, 1 GiB RAM) | Running 24/7 (730 hours/mo) | ~$7.60 |
| **Amazon EBS** | 1 x 20 GB GP3 Storage Volume | OS and Docker Images storage | ~$1.60 |
| **Amazon RDS** | 1 x `db.t4g.micro` Single-AZ (MySQL 8.4) | Managed Database Service | ~$12.80 |
| **RDS Storage** | 20 GB General Purpose SSD (gp3) | Database schemas & records | ~$2.30 |
| **AWS VPC / Egress**| Data Transfer & Nat Gateway | Egress bandwidth (~20 GB/mo) | ~$1.80 |
| **AWS CloudWatch** | Basic Monitoring & Logs | Standard Metrics & 5 GB Log Storage | ~$1.50 |
| **Total Estimated Cost (Single-AZ)** | | | **~$27.60 / month** |

---

### High-Availability, Redundancy & Multi-Region Setup Costs

To support enterprise SLAs and multi-region recovery (RPO < 1 hour, RTO < 4 hours), the following redundancy tiers are recommended:

1. **Tier 1: High Availability (Multi-AZ Deployment)**
   - RDS Multi-AZ configuration: Automatically provisions a synchronous standby replica in Availability Zone B (`Public-Subnet-2`).
   - EC2 Auto Scaling Group (min: 2, max: 4) behind an Application Load Balancer (ALB).
   - **Estimated Cost**: **~$75.00 / month**

2. **Tier 2: Multi-Region Active-Passive (Disaster Recovery)**
   - Replicates the infrastructure into the **ap-southeast-1 (Singapore)** region.
   - RDS Read Replica with asynchronous replication.
   - Route 53 Failover routing.
   - **Estimated Cost**: **~$160.00 / month**

---

### TCO Optimization Recommendations
- **Reserved Instances (RIs) / Savings Plans**: Committing to a 1-year or 3-year term for EC2 and RDS instances reduces compute costs by up to **35% - 55%**.
- **Storage Tiering**: Clean up old logs via CloudWatch retention settings and rotate compressed database backups to Amazon S3 Glacier after 14 days.
- **RDS Stop/Start**: During testing or development, stop RDS instances outside working hours to save up to **40%** on developer databases.
