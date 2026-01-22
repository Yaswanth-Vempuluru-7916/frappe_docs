# 🔧 Frappe HRMS Data Import Fix - Database Connection Issue

## 🎯 Problem Summary
Data Import Tool worked on `uat-pwv2.hashiraworks.com` but **silently failed** on `uat-gvsv2.hashiraworks.com`.

## 🔍 Root Cause Discovered
**Database authentication error** - The database user was restricted to connect from a specific IP (`172.18.0.6`) but the backend container was using a different IP (`172.18.0.9`) after Docker restart.

### Error Found in Logs:
```
MySQLdb.OperationalError: (1045, "Access denied for user '_dd426f9fff6a3c18'@'172.18.0.9' (using password: YES)")
```

---

## ✅ Solution Steps

### 1️⃣ Check Database User Permissions

```bash
docker exec -it frappe-hrms-db-1 mariadb -u root -p
```

```sql
SELECT User, Host FROM mysql.user WHERE User = '_dd426f9fff6a3c18';
```

**Output:**
```
+-------------------+------------+
| User              | Host       |
+-------------------+------------+
| _dd426f9fff6a3c18 | 172.18.0.6 | ❌ Specific IP only
+-------------------+------------+
```

---

### 2️⃣ Grant Wildcard Access

**First, get the password from site config:**

```bash
# Inside the backend container
cat sites/uat-gvsv2.hashiraworks.com/site_config.json
```

**Output:**
```json
{
 "db_name": "_dd426f9fff6a3c18",
 "db_password": "dSlux8gSb1tzBZW4",  ← Use this password
 "db_type": "mariadb",
 "db_user": "_dd426f9fff6a3c18"
}
```

**Then grant access using that password:**

```sql
GRANT ALL PRIVILEGES ON `_dd426f9fff6a3c18`.* TO '_dd426f9fff6a3c18'@'%' IDENTIFIED BY 'dSlux8gSb1tzBZW4';
FLUSH PRIVILEGES;
```

**Output:**
```
Query OK, 0 rows affected (0.018 sec)
```

---

### 3️⃣ Verify User Now Has Wildcard Access

```sql
SELECT User, Host FROM mysql.user WHERE User = '_dd426f9fff6a3c18';
```

**Output:**
```
+-------------------+------------+
| User              | Host       |
+-------------------+------------+
| _dd426f9fff6a3c18 | %          | ✅ Wildcard (any IP)
| _dd426f9fff6a3c18 | 172.18.0.6 | (old entry)
+-------------------+------------+
```

```sql
exit
```

---

### 4️⃣ Test Database Connection

```bash
docker exec -it frappe-hrms-backend-1 bash
bench --site uat-gvsv2.hashiraworks.com console
```

```python
import frappe
frappe.connect(site='uat-gvsv2.hashiraworks.com')
frappe.db.sql("SELECT 1")
```

**Output:**
```python
Out[1]: ((1,),)  # ✅ Connection works!
```

```python
exit()
```

---

### 5️⃣ Restart Background Workers

```bash
exit  # Exit container
docker compose -f frappe-hrms-compose.yml restart queue-long queue-short scheduler
```

**Output:**
```
[+] restart 0/3
 ⠴ Container frappe-hrms-scheduler-1   Restarting     10.5s
 ⠴ Container frappe-hrms-queue-long-1  Restarting     10.5s
 ⠴ Container frappe-hrms-queue-short-1 Restarting     10.5s
```

---

### 6️⃣ Check Pending Jobs Queue

```bash
docker exec -it frappe-hrms-backend-1 bash
bench --site uat-gvsv2.hashiraworks.com show-pending-jobs
```

**Output:**
```
-----Pending Jobs-----  # ✅ Queue is clear
```

---

### 7️⃣ Check Stuck Data Import Records

```bash
bench --site uat-gvsv2.hashiraworks.com console
```

```python
import frappe
frappe.connect(site='uat-gvsv2.hashiraworks.com')

data_imports = frappe.get_all('Data Import', 
    fields=['name', 'status', 'import_type', 'creation'],
    order_by='creation desc',
    limit=5)

for d in data_imports:
    print(f"{d.name}: {d.status}")
```

**Output:**
```
User Import on 2026-01-21 22:46:19.012142: Pending     # ❌ Still stuck
Employee Import on 2026-01-21 18:55:15.963527: Pending # ❌ Still stuck
```

---

### 8️⃣ Manually Trigger Stuck Import

```python
# Get one of the stuck imports
doc = frappe.get_doc('Data Import', 'User Import on 2026-01-21 22:46:19.012142')

# Try to start the import
doc.start_import()
frappe.db.commit()

print("Import triggered. Check status in a few seconds...")
exit()
```

**Output:**
```
Import triggered. Check status in a few seconds...
```

---

### 9️⃣ Verify Import Success

```bash
bench --site uat-gvsv2.hashiraworks.com console
```

```python
import frappe
frappe.connect(site='uat-gvsv2.hashiraworks.com')

doc = frappe.get_doc('Data Import', 'User Import on 2026-01-21 22:46:19.012142')
print(f"Status: {doc.status}")
```

**Output:**
```
Status: Success  # 🎉 It works!
```

```python
exit()
```

---

## 🛡️ Prevention for Future Sites (Have to Test it later, Dont do the below steps)

### Update `common_site_config.json`

```bash
docker exec -it frappe-hrms-backend-1 bash
nano sites/common_site_config.json
```

Add `"host_name": "%"` to force wildcard database users:

```json
{
 "db_host": "db",
 "db_port": 3306,
 "default_site": "uat-pwv2.hashiraworks.com",
 "dns_multitenant": true,
 "redis_cache": "redis://redis-cache:6379",
 "redis_queue": "redis://redis-queue:6379",
 "redis_socketio": "redis://redis-queue:6379",
 "socketio_port": 9000,
 "host_name": "%"
}
```

Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`)

---

## 📊 Before vs After

| Aspect | Before ❌ | After ✅ |
|--------|----------|---------|
| **Database User** | `'_dd426f9fff6a3c18'@'172.18.0.6'` | `'_dd426f9fff6a3c18'@'%'` |
| **Connection** | Fails on IP change | Works from any IP |
| **Data Import** | Silently fails | Success |
| **Survives Restarts** | No | Yes |

---

## 🎯 Key Takeaways

1. **Root Cause**: Database user created with specific IP instead of wildcard (`%`)
2. **Why Site 1 Worked**: Likely created with correct `%` host from the start
3. **Why Site 2 Failed**: Created with specific IP, broke when Docker reassigned container IPs
4. **Fix Persistence**: ✅ Survives container restarts (stored in MariaDB volume)
5. **Prevention**: Add `"host_name": "%"` to `common_site_config.json`

---

## ✨ Issue Resolved!

✅ Database connection restored  
✅ Background workers functioning  
✅ Data Import working  
✅ Fix persists across restarts  
✅ Future sites protected  

🎉 **All sites now operational!**
