# Frappe/ERPNext/HRMS Local Development Setup

Complete guide to set up Frappe, ERPNext, and HRMS locally on macOS using your forked repositories.

## Prerequisites
```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install system dependencies
brew install git python@3.11 mariadb redis node@20

# Start services
brew services start mariadb
brew services start redis

# Secure MariaDB
mariadb-secure-installation

# Configure MariaDB for Frappe
sudo nano /opt/homebrew/etc/my.cnf
```

Add to `my.cnf`:
```ini
[mysqld]
character-set-client-handshake = FALSE
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

[mysql]
default-character-set = utf8mb4
```

Restart MariaDB:
```bash
brew services restart mariadb
```

## Installation Steps

### 1. Navigate to your workspace
```bash
cd ~/Developer/frappe-custom
```

### 2. Initialize bench with your forked Frappe
```bash
bench init frappe-bench --frappe-branch develop --frappe-path https://github.com/Yaswanth-Vempuluru-7916/frappe.git
```

### 3. Enter the bench directory
```bash
cd frappe-bench
```

### 4. Get your forked ERPNext app
```bash
bench get-app https://github.com/Yaswanth-Vempuluru-7916/erpnext.git --branch develop
```

### 5. Get your forked HRMS app
```bash
bench get-app https://github.com/Yaswanth-Vempuluru-7916/hrms.git --branch develop
```

### 6. Create a new site
```bash
bench new-site mysite.local
```

When prompted:
- MySQL root password: `root` (or your password)
- Administrator password: `admin` (or your choice)

### 7. Install apps on the site
```bash
bench --site mysite.local install-app erpnext
bench --site mysite.local install-app hrms
```

### 8. Update Redis configuration
```bash
cat > sites/common_site_config.json << 'EOF'
{
 "background_workers": 1,
 "file_watcher_port": 6787,
 "frappe_user": "yaswanth",
 "gunicorn_workers": 21,
 "live_reload": true,
 "rebase_on_pull": false,
 "redis_cache": "redis://127.0.0.1:6379",
 "redis_queue": "redis://127.0.0.1:6379",
 "redis_socketio": "redis://127.0.0.1:6379",
 "restart_supervisor_on_update": false,
 "restart_systemd_on_update": false,
 "serve_default_site": true,
 "shallow_clone": true,
 "socketio_port": 9000,
 "use_redis_auth": false,
 "webserver_port": 8000
}
EOF
```

### 9. Add site to hosts file
```bash
sudo nano /etc/hosts
```

Add this line:
```
127.0.0.1  mysite.local
```

### 10. Start bench
```bash
bench start
```

Access your site at: **http://mysite.local:8000**

**Login Credentials:**
- Username: `Administrator`
- Password: (what you set during site creation)

---

## Making Changes

### Directory Structure
```
~/Developer/frappe-custom/frappe-bench/
├── apps/
│   ├── frappe/          # Your forked Frappe
│   ├── erpnext/         # Your forked ERPNext
│   └── hrms/            # Your forked HRMS
├── sites/
│   ├── mysite.local/
│   │   └── site_config.json  # DB credentials here
│   └── common_site_config.json
└── env/                  # Virtual environment
```

### Python Changes (Backend)

1. Edit any `.py` file in `apps/frappe`, `apps/erpnext`, or `apps/hrms`
2. Changes auto-reload in development mode
3. Or manually restart:
```bash
bench restart
```

### JavaScript/CSS Changes (Frontend)

#### Option 1: Auto-rebuild (Recommended)
```bash
# Terminal 1: Keep this running
bench watch

# Terminal 2: Start bench
bench start
```

Now any JS/CSS/SCSS changes automatically rebuild when you save!

#### Option 2: Manual rebuild
```bash
# After making changes
bench build --app hrms

# Or rebuild all apps
bench build

# Or force rebuild
bench build --force
```

### Database Schema Changes

After modifying DocTypes or adding fields:
```bash
bench --site mysite.local migrate
bench --site mysite.local clear-cache
```

### Hard Refresh Browser
After changes: `Cmd + Shift + R` (macOS) or `Ctrl + Shift + R` (Linux/Windows)

---

## Git Workflow

### Making Changes
```bash
cd apps/hrms  # or frappe or erpnext

# Create a feature branch
git checkout -b my-custom-feature

# Make your changes...

# Check status
git status

# Stage changes
git add .

# Commit
git commit -m "Add custom feature"

# Push to your fork
git push origin my-custom-feature
```

### Syncing with Upstream
```bash
cd apps/hrms

# Add upstream remote (one-time setup)
git remote add upstream https://github.com/frappe/hrms.git

# Fetch latest from upstream
git fetch upstream

# Merge upstream changes
git checkout develop
git merge upstream/develop

# Push to your fork
git push origin develop
```

---

## Database Connection

### Find Database Name
```bash
cat sites/mysite.local/site_config.json
```

Look for `"db_name": "_1a2b3c4d5e6f7g8h"`

### Connect via Command Line
```bash
mysql -u root -p

# Inside MySQL
USE _1a2b3c4d5e6f7g8h;  # Your actual db_name
SHOW TABLES;
```

### Connect via GUI (MySQL Workbench, TablePlus, etc.)
- **Host:** `127.0.0.1`
- **Port:** `3306`
- **Username:** `root`
- **Password:** (your MariaDB root password)
- **Database:** `_1a2b3c4d5e6f7g8h` (from site_config.json)

### Frappe Console (Recommended for Frappe queries)
```bash
bench --site mysite.local console
```

Then in Python console:
```python
# Query database
frappe.db.sql("SELECT * FROM tabUser")

# Get all documents
frappe.db.get_all("User")

# Get specific document
frappe.get_doc("User", "Administrator")
```

---

## Common Commands
```bash
# Start development server
bench start

# Restart after Python changes
bench restart

# Watch mode (auto-rebuild JS/CSS)
bench watch

# Build specific app
bench build --app hrms

# Build all apps
bench build

# Force rebuild
bench build --force

# Run migrations
bench --site mysite.local migrate

# Clear cache
bench --site mysite.local clear-cache

# Python console with Frappe context
bench --site mysite.local console

# Backup database
bench --site mysite.local backup

# Restore database
bench --site mysite.local restore /path/to/backup.sql.gz

# View logs
tail -f logs/web.log
tail -f logs/worker.log
```

---

## Troubleshooting

### Site not loading (404 error)
- Make sure you added `127.0.0.1  mysite.local` to `/etc/hosts`
- Access via `http://mysite.local:8000` (not just `http://localhost:8000`)

### CSS/JS changes not reflecting
1. Make sure you edited `.scss` files (not `.css`)
2. Run `bench build --app <appname>`
3. Clear cache: `bench --site mysite.local clear-cache`
4. Hard refresh browser: `Cmd + Shift + R`

### Redis connection errors
- Check if Redis is running: `redis-cli ping` (should return `PONG`)
- Verify Redis config in `sites/common_site_config.json`

### Python module not found
```bash
# Make sure you're in the bench directory
cd ~/Developer/frappe-custom/frappe-bench

# Activate virtual environment
source env/bin/activate

# Reinstall apps in editable mode
pip install -e apps/frappe
pip install -e apps/erpnext
pip install -e apps/hrms
```

---

## Development Workflow

### Daily Workflow
```bash
# Terminal 1: Start services
cd ~/Developer/frappe-custom/frappe-bench
bench start

# Terminal 2: Watch for file changes (optional but recommended)
cd ~/Developer/frappe-custom/frappe-bench
bench watch

# Now make changes in your IDE and they'll auto-reload!
```

### Where to Make Changes

**Frontend (UI):**
- CSS/SCSS: `apps/*/public/scss/`
- JavaScript: `apps/*/public/js/`
- HTML Templates: `apps/*/templates/`

**Backend (Server):**
- Python: `apps/*/*/doctype/` or `apps/*/*/`
- DocTypes: Edit via UI or in `apps/*/*/doctype/*/`

**After Changes:**
- Frontend: Auto-rebuilds with `bench watch` or manually `bench build --app <appname>`
- Backend: Auto-reloads in dev mode or `bench restart`
- Schema: `bench --site mysite.local migrate`

---

## Additional Resources

- [Frappe Framework Documentation](https://frappeframework.com/docs)
- [ERPNext Documentation](https://docs.erpnext.com/)
- [Frappe Developer Guide](https://frappeframework.com/docs/user/en/basics)
- [Frappe Forum](https://discuss.frappe.io/)

---

## Notes

- Always work in feature branches, never directly in `develop`
- Keep `bench watch` running during development for auto-rebuild
- Use `bench --site mysite.local console` for testing Frappe API calls
- Database name is hashed, find it in `sites/mysite.local/site_config.json`
- Edit `.scss` files, not `.css` files (they get overwritten during build)

---

**Happy Coding! 🚀**
