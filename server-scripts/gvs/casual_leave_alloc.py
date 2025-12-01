# ==================== MONTHLY CL ALLOCATION ====================

try:
    today = frappe.utils.getdate("2025-10-01")
    current_month_start = frappe.utils.get_first_day(today)
    
    # Fetch leave period from system
    leave_period = frappe.get_all("Leave Period",
        filters={
            "is_active": 1,
            "from_date": ["<=", today],
            "to_date": [">=", today]
        },
        fields=["name", "from_date", "to_date"],
        limit=1
    )
    
    if not leave_period:
        print("ERROR: No active leave period found for today's date")
        frappe.throw("No active leave period found")
    
    leave_period = leave_period[0]
    leave_period_start = frappe.utils.getdate(leave_period.from_date)
    leave_period_end = frappe.utils.getdate(leave_period.to_date)
    
    print("\n" + "="*70)
    print("MONTHLY CL ALLOCATION - CURRENT MONTH ONLY")
    print("="*70)
    print("Today: " + str(today))
    print("Current Month: " + str(current_month_start))
    print("Leave Period: " + str(leave_period_start) + " to " + str(leave_period_end))
    print("="*70 + "\n")
    
    if today.month in [2, 4]:
        month_name = "February" if today.month == 2 else "April"
        print("Current month is " + month_name + " - CL allocation excluded for this month")
        print("Script will exit without processing")
    else:
        # Get all eligible employees
        employees = frappe.get_all("Employee",
            filters={
                "status": "Active",
                "custom_probation_end_date": ["is", "set"],
                "custom_probation_end_date": ["<", today]
            },
            fields=["name", "employee_name", "custom_probation_end_date"]
        )
    
        print("Found " + str(len(employees)) + " eligible employees\n")
        
        total_success = 0
        total_skipped = 0
        
        for emp in employees:
            try:
                probation_end = frappe.utils.getdate(emp.custom_probation_end_date)
                
                # Calculate CL start date (first day of next full month after probation)
                cl_start_month = frappe.utils.add_months(probation_end, 1)
                cl_start_date = frappe.utils.get_first_day(cl_start_month)
                
                if cl_start_date < leave_period_start:
                    cl_start_date = leave_period_start
                
                if cl_start_date > today:
                    print("Skipping " + str(emp.employee_name) + " - Not yet eligible (CL starts: " + str(cl_start_date) + ")")
                    total_skipped = total_skipped + 1
                    continue
                
                print("\n" + "-"*70)
                print("Employee: " + str(emp.employee_name) + " (" + str(emp.name) + ")")
                print("Probation End: " + str(probation_end) + " | CL Start: " + str(cl_start_date))
                print("\n cl_start_month : " + str(cl_start_month) + " cl_start_date : "+ str(cl_start_date) + "\n")
                print("-"*70)
                
                existing_allocation = frappe.get_all("Leave Allocation",
                    filters={
                        "employee": emp.name,
                        "leave_type": "Casual Leave",
                        "from_date": [">=", leave_period_start],
                        "docstatus": 1
                    },
                    fields=["name", "from_date", "to_date", "total_leaves_allocated"],
                    order_by="from_date asc",
                    limit=1
                )
                
                if existing_allocation:
                    allocation = existing_allocation[0]
                    print("Found existing allocation: " + allocation.name)
                    print("  From: " + str(allocation.from_date) + " | To: " + str(allocation.to_date))
                    print("  Current Total: " + str(allocation.total_leaves_allocated))
                    
                    month_names = ["January", "February", "March", "April", "May", "June", 
                    "July", "August", "September", "October", "November", "December"]
    
                    current_month_year = month_names[current_month_start.month - 1] + " " + str(current_month_start.year)
                
                    # Add 1 leave to existing allocation
                    print("\n  Adding 1 leave for " + current_month_year)
                    alloc_doc = frappe.get_doc("Leave Allocation", allocation.name)
                    alloc_doc.new_leaves_allocated = alloc_doc.new_leaves_allocated + 1
                    alloc_doc.flags.ignore_validate = True
                    alloc_doc.flags.ignore_mandatory = True
                    alloc_doc.save(ignore_permissions=True)
                    frappe.db.commit()
                    
                    
                    print("  SUCCESS: Updated to " + str(alloc_doc.total_leaves_allocated) + " total leaves")
                    total_success = total_success + 1
                else : 
                    print("\nNo existing allocation found - Creating new allocation...")
                    doc = frappe.get_doc({
                        "doctype": "Leave Allocation",
                        "employee": emp.name,
                        "leave_type": "Casual Leave",
                        "from_date": cl_start_date,
                        "to_date": leave_period_end,
                        "new_leaves_allocated": 1,
                        "total_leaves_allocated": 1
                    })
                    
                    doc.insert(ignore_permissions=True, ignore_mandatory=True)
                    doc.submit()
                    frappe.db.commit()
                    
                    print("SUCCESS: Created allocation " + doc.name)
                    print("Total leaves allocated: 1")
                    total_success = total_success + 1
                    
            except Exception as e:
                print("ERROR processing employee: " + str(e))
                frappe.log_error(message=str(e), title="Monthly CL Allocation Error - " + str(emp.name))
                continue
        
        print("\n" + "="*70)
        print("MONTHLY ALLOCATION COMPLETED")
        print("="*70)
        print("Successful: " + str(total_success))
        print("Skipped: " + str(total_skipped))
        print("="*70 + "\n")

except Exception as e:
    print("CRITICAL ERROR: " + str(e))
    frappe.log_error(message=str(e), title="Monthly CL Allocation - Critical Error")
                    
  
