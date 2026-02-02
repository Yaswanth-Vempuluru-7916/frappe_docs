# ==================== MONTHLY ON DUTY ALLOCATION ====================

# ========== CONSTANTS ==========
LEAVE_TYPE = "Annual Leaves"

# 🔹 ARRAY OF LEAVE POLICIES (processed one by one)
LEAVE_POLICY_NAMES = [
    "HR-LPOL-2025-00006-1",
    # "HR-LPOL-2025-00007-1",
]

# ========== EXCLUDED EMPLOYEES ==========
EXCLUDED_EMPLOYEES = []

try:
    today = frappe.utils.getdate('2026-01-02')
    current_month_start = frappe.utils.get_first_day(today)
    current_month_end = frappe.utils.get_last_day(today)

    leave_period = frappe.get_all(
        "Leave Period",
        filters={
            "is_active": 1,
            "from_date": ["<=", today],
            "to_date": [">=", today]
        },
        fields=["name", "from_date", "to_date"],
        limit=1
    )

    if not leave_period:
        frappe.throw("No active leave period found")

    leave_period = leave_period[0]
    leave_period_start = frappe.utils.getdate(leave_period.from_date)
    leave_period_end = frappe.utils.getdate(leave_period.to_date)

    leave_type_doc = frappe.get_doc("Leave Type", LEAVE_TYPE)
    max_leaves_per_period = leave_type_doc.max_leaves_allowed or 0

    MONTHLY_QUOTA = 1.25

    print("\n" + "=" * 70)
    print("MONTHLY ON DUTY ALLOCATION")
    print("=" * 70)
    print("Today:", today)
    print("Current Month:", current_month_start, "to", current_month_end)
    print("Leave Period:", leave_period_start, "to", leave_period_end)
    print("Leave Type:", LEAVE_TYPE)
    print("Monthly Quota:", MONTHLY_QUOTA)
    print("=" * 70)

    total_success = 0
    total_excluded = 0
    total_skipped_other = 0

    # ============================================================
    # 🔁 PROCESS EACH LEAVE POLICY ONE BY ONE (NO LOGIC CHANGE)
    # ============================================================
    for LEAVE_POLICY_NAME in LEAVE_POLICY_NAMES:

        print("\n" + "#" * 70)
        print("Processing Leave Policy:", LEAVE_POLICY_NAME)
        print("#" * 70)

        policy_assignments = frappe.get_all(
            "Leave Policy Assignment",
            filters={
                "leave_policy": LEAVE_POLICY_NAME,
                "docstatus": 1
            },
            fields=["employee", "employee_name"]
        )

        eligible_employees = []
        for a in policy_assignments:
            if frappe.db.get_value("Employee", a.employee, "status") == "Active":
                eligible_employees.append(a)

        for assignment in eligible_employees:
            emp_id = assignment.employee
            emp_name = assignment.employee_name

            if emp_id in EXCLUDED_EMPLOYEES:
                total_excluded += 1
                continue

            print("\n" + "-" * 70)
            print(f"Employee: {emp_name} ({emp_id})")
            print("-" * 70)

            existing_allocation = frappe.get_all(
                "Leave Allocation",
                filters={
                    "employee": emp_id,
                    "leave_type": LEAVE_TYPE,
                    "from_date": [">=", leave_period_start],
                    "to_date": ["<=", leave_period_end],
                    "docstatus": 1
                },
                fields=["name", "from_date", "to_date", "total_leaves_allocated"],
                limit=1
            )

            if existing_allocation:
                allocation = existing_allocation[0]

                approved_applications = frappe.get_all(
                    "Leave Application",
                    filters={
                        "employee": emp_id,
                        "leave_type": LEAVE_TYPE,
                        "docstatus": 1,
                        "status": "Approved",
                        "from_date": [">=", allocation.from_date]
                    },
                    fields=["total_leave_days"]
                )

                leaves_taken = sum(app.total_leave_days for app in approved_applications)
                current_balance = allocation.total_leaves_allocated - leaves_taken
                addition = MONTHLY_QUOTA

                old_total = allocation.total_leaves_allocated

                print("Previous Total Allocated :", old_total)
                print("Leaves Taken             :", leaves_taken)
                print("Balance Before           :", current_balance)
                print("Monthly Quota            :", MONTHLY_QUOTA)
                print("Attempting to Add        :", addition)

                if addition > 0:
                    alloc_doc = frappe.get_doc("Leave Allocation", allocation.name)
                    alloc_doc.new_leaves_allocated += addition
                    alloc_doc.flags.ignore_validate = True
                    alloc_doc.flags.ignore_mandatory = True
                    alloc_doc.save(ignore_permissions=True)
                    frappe.db.commit()

                    alloc_doc.reload()
                    new_total = alloc_doc.total_leaves_allocated
                    new_balance = new_total - leaves_taken

                    print("Final Total Allocated    :", new_total)
                    print("Balance After            :", new_balance)

                    if new_total > old_total:
                        print("✓ LEAVES ACTUALLY ADDED  :", new_total - old_total)
                        total_success += 1
                    else:
                        print("⚠ NO CHANGE             : ERPNext ignored allocation")
                        total_skipped_other += 1
            else:
                doc = frappe.get_doc({
                    "doctype": "Leave Allocation",
                    "employee": emp_id,
                    "leave_type": LEAVE_TYPE,
                    "from_date": current_month_start,
                    "to_date": leave_period_end,
                    "new_leaves_allocated": MONTHLY_QUOTA,
                    "total_leaves_allocated": MONTHLY_QUOTA
                })

                doc.insert(ignore_permissions=True, ignore_mandatory=True)
                doc.submit()
                frappe.db.commit()

                print("✓ NEW ALLOCATION CREATED :", MONTHLY_QUOTA)
                total_success += 1

    print("\n" + "=" * 70)
    print("MONTHLY ON DUTY ALLOCATION COMPLETED")
    print("=" * 70)
    print("Successful Allocations:", total_success)
    print("Skipped (Excluded):", total_excluded)
    print("Skipped (No Change):", total_skipped_other)
    print("=" * 70)

except Exception as e:
    print("CRITICAL ERROR:", str(e))
    frappe.log_error(str(e), "Monthly On Duty Allocation - Critical Error")
