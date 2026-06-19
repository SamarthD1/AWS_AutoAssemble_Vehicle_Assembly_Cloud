# AutoAssemble Vehicle Assembly Cloud Portal

AutoAssemble is an enterprise-grade automotive manufacturing portal designed for managing vehicle assembly operations, tracking production orders in real time, managing personnel task assignments, generating management reports, and viewing audit trails.

## 📄 Project Documentation

For detailed project requirements, architectural diagrams, system designs, and notes, please refer to the official [Google Document](https://docs.google.com/document/d/1eVY2Fit-_wNz6y82lluuRC_P6mPuux-T7gI_cD32Vfg/edit?usp=sharing).

## 🚀 Features

- **Glassmorphic Design System**: Modern visual interface using CSS variables, micro-animations, custom scrollbars, and standard font styling.
- **Double-State Theme Toggle**: Seamless light/dark mode transitions that persist to local storage and sync with OS preferences.
- **Role-Based Access Control (RBAC)**: Distinct permissions for:
  - **Administrators**: Full access, including viewing System Activity Logs.
  - **Production Managers**: Core management access (CRUD on vehicles, orders, and employees; report views).
  - **Operations Staff**: View-only records; permission to submit progress tracking updates and status changes.
- **Dashboard Visualizations**: Metric counters and dynamic charts (using Chart.js via CDN) displaying production statuses, monthly yields, and personnel workloads.
- **Reports & Data Export**: Live summaries for Vehicle Production, Employee workloads, and Assembly Line Efficiencies, with complete CSV exports.
- **Security Protections**: Safe from SQL Injection via parameterized queries, protected against CSRF via Flask-WTF tokens, and secure passwords hashed using scrypt.

---

## 🔑 Default Credentials

Use the following accounts to access the portal:

| Role | Username | Password | Access Details |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin` | `admin123` | Full access, settings, security audit logs. |
| **Production Manager** | `manager` | `manager123` | Control lines, update records, view reports. |
| **Operations Staff** | `staff` | `staff123` | View listings, update active task/order progress. |

---

## 🛠️ Project Structure

```
AWS_FINAL_Project/
├── Dockerfile               # Python Flask production image
├── docker-compose.yml       # Multi-container service orchestrator
├── requirements.txt         # Python library dependencies
├── config.py                # System environment variables and settings
├── db_helper.py             # Safe database connection pools and queries
├── auth.py                  # Session logins and access control decorators
├── app.py                   # Main Flask controller and routing
├── database.sql             # Relational MySQL schema and seed data
├── README.md                # Quickstart and general documentation
├── AWS_DEPLOYMENT.md        # Cloud production deployment guide
├── templates/               # Flask HTML templates
└── static/                  # Static styles and Javascript assets
```

---

## ⚙️ Local Deployment (Docker Compose)

The easiest way to run the entire stack is with Docker Compose. This starts both the MySQL database and the Flask web server, initializing database schemas automatically.

### Prerequisites
- Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### Start the Application
In your project directory, run:
```bash
docker compose up --build
```

### Accessing the Portal
Once both containers are running and healthy:
- Open your browser and navigate to: **`http://localhost`** (mapped to port 80).
- Sign in with any of the default accounts listed above.

### Stopping the Application
To shut down the containers while preserving database volume data:
```bash
docker compose down
```
To delete database volumes and start clean:
```bash
docker compose down -v
```

---

## 💻 Running Without Docker (Manual Setup)

If you have Python 3.11+ and MySQL running locally on your system:

### 1. Initialize the Database
Import the SQL schema and seed records into your local MySQL server:
```bash
mysql -u root -p < database.sql
```

### 2. Configure Environment Variables
Set the connection variables inside your terminal before running Flask:
```bash
export DB_HOST="localhost"
export DB_USER="your_mysql_user"
export DB_PASSWORD="your_mysql_password"
export DB_NAME="auto_assemble_db"
export DB_PORT="3306"
export FLASK_SECRET_KEY="your-custom-session-key"
```

### 3. Setup Python Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Run the Dev Server
```bash
python3 app.py
```
Open **`http://localhost:5000`** in your browser.
