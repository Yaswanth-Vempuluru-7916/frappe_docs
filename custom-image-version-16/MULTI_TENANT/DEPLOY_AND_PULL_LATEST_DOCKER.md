# 🔄 Frappe HRMS v16 – Upgrade Guide (Multi-Tenant Production)

> **Purpose**: Deploy latest code changes from forked repositories to existing production multi-tenant setup  
> **Scenario**: You have commits in your forks (frappe/erpnext/hrms) that need to be deployed  
> **Sites**: `uat-pwv2.hashiraworks.com`, `uat-gvsv2.hashiraworks.com`

---

## 📋 Prerequisites

- ✅ Running multi-tenant Frappe HRMS v16 setup
- ✅ Custom Docker image: `yaswanth1679/frappe-hrms-erpnext:version-16`
- ✅ Latest commits pushed to your forked repositories
- ✅ `apps.json` file pointing to your forks
- ✅ Docker Hub login configured

---

## 🎯 Upgrade Overview

The upgrade process involves:
1. **Rebuild** Docker image with latest code from your forks
2. **Verify** the new image contains your changes
3. **Deploy** the updated image
4. **Migrate** all sites to apply schema/code changes
5. **Fix** Traefik routing if needed
6. **Verify** sites are working

---

## 📝 Step-by-Step Upgrade Process

### Step 1: Rebuild Docker Image with Latest Code

This pulls fresh code from your GitHub forks and builds a new image.

```bash
python3 easy-install.py build \
  --apps-json apps.json \
  --containerfile images/custom/Containerfile \
  --tag yaswanth1679/frappe-hrms-erpnext:version-16 \
  --push
```

**What happens:**
- Clones latest commits from your forked repos specified in `apps.json`
- Builds new Docker image with updated code
- Pushes image to Docker Hub

**Expected output:**
```
#15 exporting to image
#15 writing image sha256:786801383d95...
#15 DONE 13.0s
The push refers to repository [docker.io/yaswanth1679/frappe-hrms-erpnext]
version-16: digest: sha256:be0bb120c616... size: 2207
```

---

### Step 2: Stop Running Containers (Preserve Data)

```bash
docker compose -f frappe-hrms-erpnext-compose.yml down
```

**⚠️ CRITICAL:** 
- **NO `-v` flag** - This preserves your volumes (database, sites, Redis data)
- Only containers are stopped, data remains intact

**Expected output:**
```
[+] down 13/13
 ✔ Container frappe-hrms-erpnext-proxy-1        Removed
 ✔ Container frappe-hrms-erpnext-frontend-1     Removed
 ...
```

---

### Step 3: Pull Updated Image

```bash
docker pull yaswanth1679/frappe-hrms-erpnext:version-16
```

**Expected output:**
```
version-16: Pulling from yaswanth1679/frappe-hrms-erpnext
Digest: sha256:be0bb120c61608115b916e67777788e4b7ace099e58303d934ef38612af81d4c
Status: Image is up to date for yaswanth1679/frappe-hrms-erpnext:version-16
```

---

### Step 4: Verify Image Contains Latest Code

#### 4a. Check Image Build Timestamp

```bash
docker image inspect yaswanth1679/frappe-hrms-erpnext:version-16 --format='{{.Created}}'
```

**Expected output:**
```
2026-02-03T05:33:15.382053268+01:00
```

The timestamp should be **recent** (within the last few minutes).

---

#### 4b. Verify Specific Code Changes (Optional but Recommended)

Check if your specific code modifications are present in the image:

```bash
docker run --rm yaswanth1679/frappe-hrms-erpnext:version-16 bash -c "
grep -A 10 'def throw_overlap_error(self, d)' /home/frappe/frappe-bench/apps/hrms/hrms/hr/doctype/leave_application/leave_application.py
"
```

**Expected output (example):**
```python
def throw_overlap_error(self, d):
    msg = _("Employee {0} has already applied for {1} between {2} and {3}").format(
        self.employee, d["leave_type"], formatdate(d["from_date"]), formatdate(d["to_date"])
    )
    frappe.throw(msg, OverlapError)
```

Replace the function name with something you actually modified to confirm your changes are present.

---

### Step 5: Start Containers with Updated Image

```bash
docker compose -f frappe-hrms-erpnext-compose.yml up -d
```

**Expected output:**
```
[+] up 13/13
 ✔ Network frappe-hrms-erpnext_default          Created
 ✔ Container frappe-hrms-erpnext-db-1           Healthy
 ✔ Container frappe-hrms-erpnext-configurator-1 Exited
 ...
```

---

### Step 6: Wait for Containers to Initialize

```bash
sleep 30
```

This gives containers time to fully start.

---

### Step 7: Verify Container Status

```bash
docker compose -f frappe-hrms-erpnext-compose.yml ps
```

**All containers should show `Up` status:**
```
NAME                                STATUS
frappe-hrms-erpnext-backend-1       Up 40 seconds
frappe-hrms-erpnext-frontend-1      Up 39 seconds
frappe-hrms-erpnext-db-1            Up 51 seconds (healthy)
...
```

---

### Step 8: Migrate Sites (CRITICAL - Applies Code Changes)

#### 8a. Migrate First Site

```bash
docker exec -it frappe-hrms-erpnext-backend-1 bench --site uat-pwv2.hashiraworks.com migrate
```

**Expected output:**
```
Migrating uat-pwv2.hashiraworks.com
Updating DocTypes for frappe        : [========================================] 100%
Updating DocTypes for erpnext       : [========================================] 100%
Updating DocTypes for hrms          : [========================================] 100%
Executing frappe.patches...
...
Queued rebuilding of search index for uat-pwv2.hashiraworks.com
```

---

#### 8b. Migrate Second Site

```bash
docker exec -it frappe-hrms-erpnext-backend-1 bench --site uat-gvsv2.hashiraworks.com migrate
```

**Expected output:**
```
Migrating uat-gvsv2.hashiraworks.com
Updating DocTypes for frappe        : [========================================] 100%
...
Queued rebuilding of search index for uat-gvsv2.hashiraworks.com
```

**⚠️ Why migrate is critical:**
- Applies database schema changes
- Runs patches from new code
- Updates DocTypes and metadata
- **Without migration, code changes won't take effect**

---

### Step 9: Clear Cache for Both Sites

#### 9a. Clear Cache - First Site

```bash
docker exec -it frappe-hrms-erpnext-backend-1 bench --site uat-pwv2.hashiraworks.com clear-cache
```

#### 9b. Clear Cache - Second Site

```bash
docker exec -it frappe-hrms-erpnext-backend-1 bench --site uat-gvsv2.hashiraworks.com clear-cache
```

**Purpose:**
- Clears Python bytecode cache
- Clears Redis cache
- Ensures new code is loaded fresh

---

### Step 10: Restart Critical Services

```bash
docker compose -f frappe-hrms-erpnext-compose.yml restart backend queue-long queue-short scheduler websocket
```

**Expected output:**
```
[+] restart 5/5
 ✔ Container frappe-hrms-erpnext-queue-short-1 Restarted
 ✔ Container frappe-hrms-erpnext-websocket-1   Restarted
 ✔ Container frappe-hrms-erpnext-queue-long-1  Restarted
 ✔ Container frappe-hrms-erpnext-backend-1     Restarted
 ✔ Container frappe-hrms-erpnext-scheduler-1   Restarted
```

**Why restart:**
- Reloads Python code in worker processes
- Ensures all services use new code
- Clears any in-memory state

---

### Step 11: Verify Deployment Health

#### 11a. Check First Site

```bash
docker exec -it frappe-hrms-erpnext-backend-1 bench --site uat-pwv2.hashiraworks.com doctor
```

**Expected output:**
```
-----Checking scheduler status-----
Workers online: 2
-----uat-pwv2.hashiraworks.com Jobs-----
```

#### 11b. Check Second Site

```bash
docker exec -it frappe-hrms-erpnext-backend-1 bench --site uat-gvsv2.hashiraworks.com doctor
```

**Expected output:**
```
-----Checking scheduler status-----
Workers online: 2
-----uat-gvsv2.hashiraworks.com Jobs-----
```

---

### Step 12: Verify Code is Deployed (Final Check)

```bash
docker exec -it frappe-hrms-erpnext-backend-1 bash -c "
grep -A 5 'def throw_overlap_error(self, d)' /home/frappe/frappe-bench/apps/hrms/hrms/hr/doctype/leave_application/leave_application.py
"
```

**Expected:** Your modified code should appear here.

---

## 🔧 Troubleshooting: Fix Traefik Routing (If Needed)

### Symptom: Internal Server Error on Sites

If you get **500 Internal Server Error** when accessing sites, check Traefik configuration.

---

### Issue: Corrupted Host Rule

The Traefik rule might be corrupted:

**Incorrect:**
```yaml
traefik.http.routers.frontend-http.rule: Hostuat-pwv2.hashiraworks.comuat-gvsv2.hashiraworks.com)
```

**Correct:**
```yaml
traefik.http.routers.frontend-http.rule: HostRegexp(`{host:.+}`)
```

---

### Fix Steps

#### 1. Stop Containers

```bash
docker compose -f frappe-hrms-erpnext-compose.yml down
```

---

#### 2. Edit Compose File

```bash
nano frappe-hrms-erpnext-compose.yml
```

Find the `frontend` service → `labels` section → Change to:

```yaml
  traefik.http.routers.frontend-http.rule: HostRegexp(`{host:.+}`)
```
---

#### 3. Verify Fix

```bash
grep "traefik.http.routers.frontend-http.rule" frappe-hrms-erpnext-compose.yml
```

**Expected output:**
```yaml
traefik.http.routers.frontend-http.rule: HostRegexp(`{host:.+}`)
```

---

#### 4. Restart Containers

```bash
docker compose -f frappe-hrms-erpnext-compose.yml up -d
```

---

#### 5. Enable DNS Multitenant (If Not Already Set)

```bash
docker exec -it frappe-hrms-erpnext-backend-1 bash
```

Inside container:

```bash
# Check current setting
cat sites/common_site_config.json | grep dns_multitenant

# Enable if not set
bench config dns_multitenant on

# Verify
cat sites/common_site_config.json | grep dns_multitenant

exit
```

**Expected in `common_site_config.json`:**
```json
{
  "dns_multitenant": true
}
```

---

#### 6. Test Sites

```bash
curl -I https://uat-pwv2.hashiraworks.com
curl -I https://uat-gvsv2.hashiraworks.com
```

**Expected response:**
```
HTTP/2 200
```

Or open in browser:
- `https://uat-pwv2.hashiraworks.com`
- `https://uat-gvsv2.hashiraworks.com`

---

## 🎯 Complete Upgrade Script (All Steps Combined)

```bash
#!/bin/bash

# Step 1: Rebuild image with latest code
python3 easy-install.py build \
  --apps-json apps.json \
  --containerfile images/custom/Containerfile \
  --tag yaswanth1679/frappe-hrms-erpnext:version-16 \
  --push

# Step 2: Stop containers (preserve volumes)
docker compose -f frappe-hrms-erpnext-compose.yml down

# Step 3: Pull updated image
docker pull yaswanth1679/frappe-hrms-erpnext:version-16

# Step 4: Verify image timestamp
echo "=== Image Build Time ==="
docker image inspect yaswanth1679/frappe-hrms-erpnext:version-16 --format='{{.Created}}'

# Step 5: Start containers
docker compose -f frappe-hrms-erpnext-compose.yml up -d

# Step 6: Wait for initialization
sleep 30

# Step 7: Check container status
docker compose -f frappe-hrms-erpnext-compose.yml ps

# Step 8: Migrate sites
echo "=== Migrating Sites ==="
docker exec -it frappe-hrms-erpnext-backend-1 bench --site uat-pwv2.hashiraworks.com migrate
docker exec -it frappe-hrms-erpnext-backend-1 bench --site uat-gvsv2.hashiraworks.com migrate

# Step 9: Clear cache
echo "=== Clearing Cache ==="
docker exec -it frappe-hrms-erpnext-backend-1 bench --site uat-pwv2.hashiraworks.com clear-cache
docker exec -it frappe-hrms-erpnext-backend-1 bench --site uat-gvsv2.hashiraworks.com clear-cache

# Step 10: Restart services
docker compose -f frappe-hrms-erpnext-compose.yml restart backend queue-long queue-short scheduler websocket

# Step 11: Verify deployment
echo "=== Verifying Deployment ==="
docker exec -it frappe-hrms-erpnext-backend-1 bench --site uat-pwv2.hashiraworks.com doctor
docker exec -it frappe-hrms-erpnext-backend-1 bench --site uat-gvsv2.hashiraworks.com doctor

# Step 12: Test sites
echo "=== Testing Sites ==="
curl -I https://uat-pwv2.hashiraworks.com
curl -I https://uat-gvsv2.hashiraworks.com

echo "=== Upgrade Complete ==="
```

---

## 📊 Verification Checklist

After upgrade, verify:

- ✅ Image build timestamp is recent
- ✅ Your code changes are present in the image
- ✅ All containers are `Up` and healthy
- ✅ Both sites migrated successfully
- ✅ Scheduler shows "Workers online: 2"
- ✅ Sites accessible via HTTPS
- ✅ No internal server errors
- ✅ DNS multitenant enabled
- ✅ Traefik rule is `HostRegexp(\`{host:.+}\`)`

---

## ⚠️ Important Notes

### Data Safety

- ✅ **`docker compose down`** - Safe, preserves volumes
- ❌ **`docker compose down -v`** - DELETES ALL DATA (never use during upgrade)

### Migration is Mandatory

- **Every upgrade requires migration** for both sites
- Migration applies schema changes from new code
- Skipping migration = code won't work properly

### Multi-Tenant Configuration

- `HostRegexp(\`{host:.+}\`)` - Routes ALL domains to frontend
- `dns_multitenant: true` - Frappe handles site routing internally
- Each site has separate database
- Sites share same codebase but isolated data

### Cache Clearing

- Always clear cache after code changes
- Ensures Python bytecode is regenerated
- Prevents stale code from running

---

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-03  
**Tested On:** Frappe v16, ERPNext v16, HRMS v16
