

# 📘 Frappe Fork Setup – Branching & Upstream Strategy (v16)

This document explains how we structured our fork of
Frappe
for proper UAT and Production separation using the official `version-16` branch.

---

# 🏗 Initial Setup Steps

## 1️⃣ Clone Our Organization Fork

```bash
git clone https://github.com/PossibleWorks/frappe.git
cd frappe
```

Verify remote:

```bash
git remote -v
```

Output:

```
origin  https://github.com/PossibleWorks/frappe.git (fetch)
origin  https://github.com/PossibleWorks/frappe.git (push)
```

At this point:

* `origin` → Our organization fork

---

## 2️⃣ Add Official Frappe Repository as Upstream

```bash
git remote add upstream https://github.com/frappe/frappe.git
```

Verify:

```bash
git remote -v
```

Output:

```
origin    https://github.com/PossibleWorks/frappe.git (fetch)
origin    https://github.com/PossibleWorks/frappe.git (push)
upstream  https://github.com/frappe/frappe.git (fetch)
upstream  https://github.com/frappe/frappe.git (push)
```

Now:

* `origin` → Our fork
* `upstream` → Official Frappe repo

---

## 3️⃣ Fetch Official Branches

```bash
git fetch upstream
```

This downloaded all official branches including:

```
upstream/version-16
upstream/version-16-hotfix
```

No local branches were modified.

---

## 4️⃣ Create Clean Mirror Branch (Tracking Official)

```bash
git checkout -b version-16-upstream upstream/version-16
```

Output:

```
branch 'version-16-upstream' set up to track 'upstream/version-16'.
Switched to a new branch 'version-16-upstream'
```

Push to our fork:

```bash
git push origin version-16-upstream
```

Now our fork contains:

```
version-16-upstream
```

This branch is a **clean mirror of official version-16**.

---

## 5️⃣ Create UAT Branch

```bash
git checkout -b uat
git push origin uat
```

UAT is created from `version-16-upstream`.

---

## 6️⃣ Create Production Branch

```bash
git checkout version-16-upstream
git checkout -b prod
git push origin prod
```

Production is also created from clean mirror.

---

## 7️⃣ Create Backup Branch (Safety)

```bash
git checkout version-16-upstream
git checkout -b version-16-upstream-backup
git push origin version-16-upstream-backup
```

This acts as an emergency rollback reference.

---

# 🧠 Now Your Safe Structure Is

```
version-16-upstream          ← Official mirror (DO NOT DEVELOP HERE)
version-16-upstream-backup   ← Safety copy
uat                          ← Testing environment
prod                         ← Production environment
develop                      ← Ignored
```

---

# 🔥 Extremely Important Rules

### ❌ Never Do This

```bash
git merge upstream/version-16
```

While sitting on:

* uat
* prod

---

### ✅ Always Do This

When official Frappe releases updates:

```bash
git fetch upstream
git checkout version-16-upstream
git merge upstream/version-16
git push origin version-16-upstream
```

STOP.

At this point:

* uat unchanged
* prod unchanged

---

### When Ready to Test Updates

```bash
git checkout uat
git merge version-16-upstream
```

Test thoroughly.

---

### When UAT is Stable

```bash
git checkout prod
git merge uat
```

Deploy to production.

---

# 🏢 Environment Promotion Flow

```
Official Frappe
        ↓
version-16-upstream (mirror)
        ↓
uat (testing)
        ↓
prod (live)
```


# 📘 Developing a New Feature & Syncing with Official Updates

This explains how to:

* Develop a new feature
* Merge it safely into UAT
* Later sync official Frappe updates
* Without breaking `prod`

---

# 🧑‍💻 1️⃣ Creating a New Feature

⚠️ Never develop directly on `uat`.

Always create a feature branch from `uat`.

```bash
git checkout uat
git pull origin uat
git checkout -b feature/attendance-auto-deduction
```

Work on your feature.

Commit changes:

```bash
git add .
git commit -m "feat: attendance auto deduction logic"
```

Push:

```bash
git push origin feature/attendance-auto-deduction
```

Create Pull Request:

```
feature/attendance-auto-deduction → uat
```

After review → merge into `uat`.

---

# 🧠 Flow Now Looks Like

```
version-16-upstream
        ↓
uat  ← your feature merged here
        ↓
prod (unchanged)
```

---

# 🔄 2️⃣ Later: Official Frappe Releases Updates

When
Frappe
releases updates to `version-16`:

---

## Step A — Sync Official Code

```bash
git fetch upstream
git checkout version-16-upstream
git merge upstream/version-16
git push origin version-16-upstream
```

At this point:

* uat is untouched
* prod is untouched

---

## Step B — Bring Official Updates Into UAT

Now merge official updates into uat:

```bash
git checkout uat
git merge version-16-upstream
```

Now UAT contains:

* Your features
* Latest official Frappe updates

Fix conflicts if any.
Test everything.

---

## Step C — Promote to Production (When Stable)

```bash
git checkout prod
git merge uat
```

Deploy.

---

# 🔥 Extremely Important Rules

### ❌ Never

* Develop on `version-16-upstream`
* Merge upstream directly into `prod`
* Develop directly on `prod`

---

### ✅ Always Follow

```
feature → uat → prod
```

And for official updates:

```
upstream → version-16-upstream → uat → prod
```

---

# 🎯 Final Visual Model

```
Official Frappe
        ↓
version-16-upstream
        ↓
uat (features + official updates tested)
        ↓
prod (stable only)
```

---
