
# ✅ Deleting a Frappe Site in Docker (STANDARD & SAFE METHOD)

This guide documents the **exact steps** to make `bench drop-site` work
properly in a **Docker-based Frappe / ERPNext setup**.

---

## 🧠 Background (Why this is needed)

In Docker setups:
- MariaDB root password is stored as an **environment variable**
- `bench drop-site` requires **root DB access**
- By default, bench does NOT know the DB root password
- We must teach bench the root credentials **once**

---

## 1️⃣ Get MariaDB ROOT password (from DB container)

```bash
docker exec -it frappe-hrms-db-1 env | grep -i root
````

Example output:

```text
MYSQL_ROOT_PASSWORD=ee0d7457e
```

👉 Copy this password.

---

## 2️⃣ Enter the backend container (where bench exists)

```bash
docker exec -it frappe-hrms-backend-1 bash
cd ~/frappe-bench
```

---

## 3️⃣ Configure bench with DB root credentials (ONE-TIME SETUP)

```bash
bench set-config -g root_login root
bench set-config -g root_password ee0d7457e
```

---

## 4️⃣ Verify configuration (IMPORTANT)

```bash
cat sites/common_site_config.json
```

Expected keys:

```json
{
  "root_login": "root",
  "root_password": "ee0d7457e"
}
```

If present → bench is now DB-authorized ✅

---

## 5️⃣ Delete a site using STANDARD bench command

### Recommended (fast, no backup)

```bash
bench drop-site <site-name> --no-backup
```

### Example:

```bash
bench drop-site uat-gvsv2.hashiraworks.com --no-backup
```

What this does:

* Drops database
* Drops DB user
* Moves site to `archived/sites`
* Removes site from `sites/`

---

## 6️⃣ Verify deletion

```bash
ls sites/
```

Site should NOT be listed.

---

## 7️⃣ (Optional) Permanently delete archived site

```bash
rm -rf archived/sites/<site-name>
```

---

## 🔁 From now on (NORMAL USAGE)

After steps 1–4 are done once, you can always use:

```bash
bench drop-site <site-name>
```

or

```bash
bench drop-site <site-name> --no-backup
```

without any manual DB work.

---

## ⚠️ Notes

* `--force` does NOT bypass DB root auth
* `DB_PASSWORD` ≠ MariaDB root password
* `SITE_ADMIN_PASS` ≠ MariaDB root password
* Root DB password comes ONLY from DB container env

---
