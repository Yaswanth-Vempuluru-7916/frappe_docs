
# Custom ERPNext with Frappe, ERPNext & HRMS (All from My Forks)

> **Fully Custom ERPNext v16-dev**  
> Built from **my GitHub forks**  
> Deployed via **Docker + Docker Hub**  
> Live at: `http://18.130.30.41:8080`

---

## Overview

This project runs a **production-ready ERPNext** using **custom versions** of:

- [Frappe](https://github.com/Yaswanth-Vempuluru-7916/frappe) (`develop`)
- [ERPNext](https://github.com/Yaswanth-Vempuluru-7916/erpnext) (`develop`)
- [HRMS](https://github.com/Yaswanth-Vempuluru-7916/hrms) (`develop`)

All code is pulled from **my GitHub forks**, built into a **custom Docker image**, and deployed using `frappe_docker`.

---

## Step-by-Step Setup (3 Steps + Critical Fix)

### Step 1: Hardcode Frappe Repo & Branch

Modified `easy-install.py` to **always use my Frappe fork**:

```bash
# In easy-install.py
--frappe-path=https://github.com/Yaswanth-Vempuluru-7916/frappe
--frappe-branch=develop
```

> This ensures **Frappe is from my fork**, not official.

---

### Step 2: Build & Push Custom Docker Image

```bash
# apps.json (ERPNext + HRMS from my forks)
cat > apps.json << 'EOF'
[
  {
    "url": "https://github.com/Yaswanth-Vempuluru-7916/erpnext",
    "branch": "develop",
    "name": "erpnext"
  },
  {
    "url": "https://github.com/Yaswanth-Vempuluru-7916/hrms",
    "branch": "develop",
    "name": "hrms"
  }
]
EOF

# Build & push
python3 easy-install.py build \
  --apps-json apps.json \
  --containerfile images/custom/Containerfile \
  --tag yaswanth1679/erpnext:custom-dev \
  --push
```

**Result**:  
Docker Hub Image: [`yaswanth1679/erpnext:custom-dev`](https://hub.docker.com/repository/docker/yaswanth1679/erpnext/general)

---

### Step 3: Deploy to Production (with `.env` Fix)

```bash
python3 easy-install.py deploy \
  --project myerp \
  --sitename 18.130.30.41 \
  --email yaswanthvempuluru@gmail.com \
  --image yaswanth1679/erpnext:custom-dev \
  --app erpnext \
  --app hrms
```

---

### Critical Fix: `.env` File (Required!)

After first deploy, **edit `~/myerp.env`**:

```bash
# Remove these (cause :v15.88.1 tag error)
sed -i '/ERPNEXT_VERSION/d' ~/myerp.env

# Set correct image name (without tag)
sed -i 's|CUSTOM_IMAGE=yaswanth1679/erpnext:custom-dev|CUSTOM_IMAGE=yaswanth1679/erpnext|' ~/myerp.env

# Add tag separately
echo "CUSTOM_TAG=custom-dev" >> ~/myerp.env
```

**Final `myerp.env` must contain:**

```env
CUSTOM_IMAGE=yaswanth1679/erpnext
CUSTOM_TAG=custom-dev
```

> **Why?**  
> `CUSTOM_IMAGE:custom-dev` → invalid Docker reference  
> `CUSTOM_IMAGE=repo` + `CUSTOM_TAG=tag` → correct

---

## Proof of Custom Code

| Evidence | Command / Link |
|--------|---------------|
| **Docker Image** | `yaswanth1679/erpnext:custom-dev` |
| **All containers use my image** | `docker ps` |
| **Frappe from my fork** | `--frappe-path=https://github.com/Yaswanth-Vempuluru-7916/frappe` |
| **ERPNext & HRMS from my forks** | `apps.json` + commit hashes |
| **Live containers** | `docker ps` → 7 containers running my image |

---

## Running Containers

```bash
docker ps
```

```text
CONTAINER ID   IMAGE                              NAMES
abad6f59f140   yaswanth1679/erpnext:custom-dev    myerp-backend-1
1c7e9a346804   yaswanth1679/erpnext:custom-dev    myerp-frontend-1
...            yaswanth1679/erpnext:custom-dev    myerp-queue-*, myerp-scheduler-1, etc.
```

**All ERPNext services run from MY image.**

---

## Source Repositories

| App       | Repository |
|-----------|------------|
| Frappe    | https://github.com/Yaswanth-Vempuluru-7916/frappe |
| ERPNext   | https://github.com/Yaswanth-Vempuluru-7916/erpnext |
| HRMS      | https://github.com/Yaswanth-Vempuluru-7916/hrms |

---

## Future Updates : YET TO BE TESTED

To update:

```bash
# Rebuild image
python3 easy-install.py build --push --no-cache ...

# Upgrade
python3 easy-install.py upgrade --project myerp --image yaswanth1679/erpnext:custom-dev
```

---

## Author

**Yaswanth Vempuluru**  
GitHub: [@Yaswanth-Vempuluru-7916](https://github.com/Yaswanth-Vempuluru-7916)  
Docker Hub: [yaswanth1679](https://hub.docker.com/u/yaswanth1679)

---

> **This ERPNext instance is 100% built from my custom code.**  
> **No official sources used.**
