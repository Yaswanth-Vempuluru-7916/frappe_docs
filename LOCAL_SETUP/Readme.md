
# Frappe v16 Local Setup (macOS – Homebrew + pyenv)

This document describes the complete, verified steps to set up a **local Frappe v16 + ERPNext + HRMS** environment on macOS using Homebrew, pyenv, MariaDB, and virtualenv.

---

## 1. Install System Dependencies

```bash
brew install python
brew install mariadb
brew services start mariadb
brew install pyenv
````

---

## 2. Create Project Directory

```bash
mkdir frappe-local
cd frappe-local
```

---

## 3. Install and Configure Python via pyenv

```bash
pyenv install 3.14.2
pyenv local 3.14.2
```

Edit shell config:

```bash
nano ~/.zshrc
```

Add the following lines:

```bash
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
```

Reload shell:

```bash
source ~/.zshrc
```

Verify Python:

```bash
python --version
which python
pip --version
```

---

## 4. Configure MariaDB for Frappe

Login as root:

```bash
sudo mariadb
```

Run the following SQL commands:

```sql
CREATE USER 'frappe'@'localhost' IDENTIFIED BY 'frappe';
GRANT ALL PRIVILEGES ON *.* TO 'frappe'@'localhost' WITH GRANT OPTION;
FLUSH PRIVILEGES;

SELECT user, host, plugin FROM mysql.user WHERE user='frappe';

ALTER USER 'frappe'@'localhost'
IDENTIFIED VIA mysql_native_password USING PASSWORD('sudheer');

FLUSH PRIVILEGES;
EXIT;
```

---

## 5. MariaDB UTF-8 Configuration

Edit Frappe MariaDB config:

```bash
sudo nano /opt/homebrew/etc/my.cnf.d/frappe.cnf
```

Add:

```ini
[mysqld]
character-set-client-handshake = FALSE
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

[mysql]
default-character-set = utf8mb4

[client]
default-character-set = utf8mb4
```

Restart MariaDB:

```bash
brew services restart mariadb
```

Verify login:

```bash
mariadb -u frappe -p
```

---

## 6. Create Python Virtual Environment

```bash
python -m venv venv
source venv/bin/activate
```

Install bench:

```bash
pip install frappe-bench
bench --version
```

---

## 7. Initialize Frappe Bench

```bash
bench init frappe-bench \
  --frappe-branch version-16 \
  --frappe-path https://github.com/Yaswanth-Vempuluru-7916/frappe.git \
  --no-backups
```

---

## 8. Start Bench Console (Separate Terminal)

Open a **new terminal**:

```bash
cd frappe-local
source venv/bin/activate
```

This terminal will run the bench console later.

---

## 9. Install ERPNext and HRMS Apps

Back in the **original terminal**:

```bash
cd frappe-bench
```

Get apps:

```bash
bench get-app https://github.com/Yaswanth-Vempuluru-7916/erpnext.git --branch version-16
bench get-app https://github.com/Yaswanth-Vempuluru-7916/hrms.git --branch version-16
```

---

## 10. Create Site

```bash
bench new-site hrms-pw.local \
  --db-root-username frappe \
  --db-root-password sudheer
```

---

## 11. Install Apps on Site

```bash
# Install ERPNext first
bench --site hrms-pw.local install-app erpnext

# Install HRMS next
bench --site hrms-pw.local install-app hrms
```

---

## 12. Configure Local Domain

Edit hosts file:

```bash
sudo nano /etc/hosts
```

Add:

```text
127.0.0.1  hrms-pw.local
```

---

## 13. Start Bench and Access Site

```bash
bench start
```

Access in browser:

```
http://hrms-pw.local:8000
```

---

## ✅ Setup Complete

Your local **Frappe v16 + ERPNext + HRMS** environment is now ready.



Just say the word.
```
