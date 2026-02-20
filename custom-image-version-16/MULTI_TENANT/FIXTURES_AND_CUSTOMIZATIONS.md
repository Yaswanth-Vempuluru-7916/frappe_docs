# 📦 Frappe Customizations – Multi-Tenant Usage Guide

## 🎯 Purpose

`frappe_customizations` is a **central custom app** used to manage:

* Custom Fields
* Custom DocTypes
* Workflows
* Property Setters
* Scripts
* Business-specific extensions

This ensures all customizations are **code-driven, upgrade-safe, and automatically applied across all tenants**.

---

## 🚀 Installation (Multi-Tenant Setup)

### 1️⃣ Get the app

```bash
bench get-app https://github.com/<your-org>/frappe_customizations
```

---

### 2️⃣ Install app in all sites

```bash
bench --site site1 install-app frappe_customizations
bench --site site2 install-app frappe_customizations
# or
bench --site all list-apps  # verify
```

Every site must have this app installed for fixtures and schema sync to work.

---

## 🧩 Adding Customizations

### ⭐ Custom Fields / Workflows / Scripts (Fixtures approach)

1. Create customization via UI (Customize Form, Workflow Builder, etc.)
2. Add filters in `hooks.py`

Example:

```python
fixture_doctypes_with_custom_fields = ["Leave Type", "Leave Application"]

fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [["dt", "in", fixture_doctypes_with_custom_fields]],
    },
]
```

3. Export fixtures from a source site:

```bash
bench --site hrms-pw.local export-fixtures --app frappe_customizations
```

4. Commit and push:

```bash
cd apps/frappe_customizations
git add .
git commit -m "Export fixtures"
git push
```

---

### ⭐ Custom DocTypes (Code approach)

1. Create DocType in developer mode
2. Ensure **Module = frappe_customizations**
3. Save → files generated in app

Optional fixture export (for metadata control):

```python
{
    "doctype": "DocType",
    "filters": [["name", "in", ["Leave Supporting Documents"]]],
}
```

Then:

```bash
bench --site hrms-pw.local export-fixtures --app frappe_customizations
```

---

## 🔄 Propagating Changes to All Tenants

After pushing code:

### Local / Dev

```bash
bench --site all migrate
```

### Production (Docker flow)

```
Push → Build Image → Deploy → bench migrate all
```

This will:

* Create tables for new DocTypes
* Apply Custom Fields
* Sync metadata across all sites

---

## 🧠 Mental Model

| Customization Type | Propagation Method |
| ------------------ | ------------------ |
| Custom Field       | Fixture            |
| Workflow           | Fixture            |
| Property Setter    | Fixture            |
| Client Script      | Fixture            |
| New DocType        | Code               |
| Python logic       | Code               |

---

## ✅ Outcome

Following this flow guarantees:

* No per-site manual customization
* All existing sites updated automatically
* New sites inherit customizations immediately
* Upgrade-safe architecture

---

## 🏁 Golden Rule

> **Create once → export → commit → build → migrate → all tenants updated**

---
