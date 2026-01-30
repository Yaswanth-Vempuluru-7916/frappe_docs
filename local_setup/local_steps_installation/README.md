
# **Frappe + ERPNext + HRMS Setup Documentation (MacOS)**

---

## **1. Install Python Using pyenv**

```bash
# Install Python 3.14 first
pyenv install 3.14

# Install Python 3.12.8 (used for Frappe)
pyenv install 3.12.8
pyenv local 3.12.8

# Verify installation
python --version          # Should show: Python 3.12.8
which python              # Should point to ~/.pyenv/versions/3.12.8/bin/python
pip --version             # Should match Python 3.12.8
```

---

## **2. Install and Start Dependencies**

```bash
# Start MariaDB and Redis
brew services start mariadb
brew services start redis

# Secure MariaDB installation
mariadb-secure-installation
```

---

## **3. Configure MariaDB for Frappe**

```bash
# Login as root
sudo mariadb
```

Inside MariaDB:

```sql
-- Create frappe user
CREATE USER 'frappe'@'localhost' IDENTIFIED BY 'frappe';

-- Grant privileges
GRANT ALL PRIVILEGES ON *.* TO 'frappe'@'localhost' WITH GRANT OPTION;

-- Apply privileges
FLUSH PRIVILEGES;

-- Check plugin
SELECT user, host, plugin FROM mysql.user WHERE user='frappe';

-- Alter user to ensure mysql_native_password authentication
ALTER USER 'frappe'@'localhost'
IDENTIFIED VIA mysql_native_password
USING PASSWORD('frappe');

-- Apply privileges
FLUSH PRIVILEGES;

-- Optional: change password to 'yaswanth'
ALTER USER 'frappe'@'localhost' IDENTIFIED BY 'yaswanth';
FLUSH PRIVILEGES;

-- Exit MariaDB
EXIT;
```

> ✅ Now you should be able to log in as:

```bash
mariadb -u frappe -p
# Enter password: yaswanth
```

---

## **4. MariaDB Configuration Files (Required for Frappe Stability)**

```bash
# Login to MariaDB as root (verification)
sudo mariadb

# Login as frappe user (verification)
mariadb -u frappe -p
```

Edit MariaDB configuration files:

```bash
# Main MariaDB config
sudo nano /opt/homebrew/etc/my.cnf

# Frappe-specific MariaDB config
sudo nano /opt/homebrew/etc/my.cnf.d/frappe.cnf
```

> These files are used to set:

* character-set-server
* collation-server
* innodb settings
* max_connections
* sql-mode compatibility for Frappe

Restart MariaDB after config changes:

```bash
brew services restart mariadb
```

Test connection again:

```bash
mariadb -u frappe -p
```

---

## **5. Initialize Bench Environment**

```bash
# Create a Python virtual environment
python -m venv venv
source venv/bin/activate

# Install bench
pip install frappe-bench

# Verify bench
bench --version
```

---

## **6. Initialize Frappe Bench**

```bash
# Initialize bench with your forked Frappe repository
bench init frappe-bench \
  --frappe-branch version-16 \
  --frappe-path https://github.com/Yaswanth-Vempuluru-7916/frappe.git \
  --no-backups
```

---

## **7. Go to Bench Directory**

```bash
cd frappe-bench
```

---

## **8. Alter MariaDB Frappe User (Before get-app)**

```bash
sudo mariadb
```

Inside MariaDB:

```sql
ALTER USER 'frappe'@'localhost' IDENTIFIED BY 'yaswanth';
FLUSH PRIVILEGES;
EXIT;
```

> This ensures Frappe can connect to MariaDB without authentication issues.

---

## **9. Get ERPNext and HRMS Apps**

```bash
bench get-app https://github.com/Yaswanth-Vempuluru-7916/erpnext.git --branch version-16
bench get-app https://github.com/Yaswanth-Vempuluru-7916/hrms.git --branch version-16
```

---

## **10. Create a New Site**

```bash
bench new-site hrms-pw.local --db-root-username frappe --db-root-password yaswanth
```

---

## **11. Install Apps on the Site**

```bash
# ERPNext first
bench --site hrms-pw.local install-app erpnext

# HRMS next
bench --site hrms-pw.local install-app hrms
```

---

## **12. Setup Redis and Start Bench**

```bash
# If Redis was stopped
brew services stop redis

# Setup Redis in Bench
bench setup redis

# Start Bench (terminal must remain open)
bench start
```

---

> ⚠️ **Important: bench not found in a new terminal**

```bash
cd ~/Developer/frappe-local
source venv/bin/activate
cd frappe-bench
```

---

## **13. Add Site Entry to Hosts File**

```bash
sudo nano /etc/hosts
```

Add:

```text
127.0.0.1  hrms-pw.local
```

Access your site at:
👉 **[http://hrms-pw.local:8000](http://hrms-pw.local:8000)**

---
