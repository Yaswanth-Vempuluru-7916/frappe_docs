# Server Script: Historical Monthly CL Allocation (April to Today)
# Script Type: Scheduler Event
# Event: Cron - 36 14 * * *
# NOTE: Do NOT use import statements in Server Scripts - modules are pre-loaded

def get_current_leave_period_dates(reference_date):
    """Return current Indian financial year (April – March)"""
    year = reference_date.year
    
    if reference_date.month >= 4:
        start_date = frappe.utils.getdate(str(year) + "-04-01")
        end_date   = frappe.utils.getdate(str(year + 1) + "-03-31")
    else:
        start_date = frappe.utils.getdate(str(year - 1) + "-04-01")
        end_date   = frappe.utils.getdate(str(year) + "-03-31")
    
    return start_date, end_date

def get_cl_start_date(probation_end_date, leave_period_start):
    """Get CL start date (first day of next full month after probation)"""
    cl_start_month = frappe.utils.add_months(probation_end_date, 1)
    cl_start = frappe.utils.get_first_day(cl_start_month)
    
    if cl_start < leave_period_start:
        return leave_period_start
    
    return cl_start

def should_allocate_cl_this_month(current_month):
    """Check if CL should be allocated for this month (exclude Feb & April)"""
    return current_month not in [2, 4]

def get_cl_allocation_for_month(employee, month_start, month_end):
    """Check if CL already allocated for this specific month (check for overlaps)"""
    allocations = frappe.get_all("Leave Allocation",
        filters={
            "employee": employee,
            "leave_type": "Casual Leave",
            "docstatus": 1,
            "from_date": ["<=", month_end],
            "to_date": [">=", month_start]
        },
        limit=1
    )
    return len(allocations) > 0

def format_month_year(date_obj):
    """Safe date formatting for server scripts"""
    month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return month_names[date_obj.month] + " " + str(date_obj.year)

def allocate_monthly_cl_direct(employee, month_start, month_end):
    """Allocate 1 CL for specific month"""
    try:
        # Check for overlapping allocations first
        existing = frappe.get_all("Leave Allocation",
            filters={
                "employee": employee,
                "leave_type": "Casual Leave",
                "from_date": ["<=", month_end],
                "to_date": [">=", month_start]
            },
            fields=["name", "from_date", "to_date", "total_leaves_allocated", "docstatus"]
        )
        
        if existing:
            print("Skipping " + str(employee) + " for " + format_month_year(month_start) + " - Existing allocation found")
            return False
        
        # Create allocation document using get_doc with dictionary
        doc = frappe.get_doc({
            "doctype": "Leave Allocation",
            "employee": employee,
            "leave_type": "Casual Leave",
            "from_date": month_start,
            "to_date": month_end,
            "total_leaves_allocated": 1,
            "new_leaves_allocated": 1
        })
        
        # Insert and submit
        doc.insert(ignore_permissions=True, ignore_mandatory=True)
        doc.submit()
        
        # Commit to database
        frappe.db.commit()
        
        print("SUCCESS: CL allocated for " + str(employee) + " - " + format_month_year(month_start) + " - ID: " + doc.name)
        return True

    except Exception as e:
        error_msg = "Error allocating CL for " + str(employee) + " (" + format_month_year(month_start) + "): " + str(e)
        print(error_msg)
        frappe.log_error(message=error_msg, title="CL Allocation Failed - " + str(employee))
        frappe.db.rollback()
        return False

def get_all_months_between(start_date, end_date):
    """Get all months between start and end date"""
    months = []
    current = frappe.utils.get_first_day(start_date)
    
    while current <= end_date:
        month_start = frappe.utils.get_first_day(current)
        month_end = frappe.utils.get_last_day(current)
        months.append((month_start, month_end))
        current = frappe.utils.add_months(current, 1)
    
    return months

# ==================== MAIN EXECUTION ====================

try:
    today = frappe.utils.getdate()

    # Get current leave period
    period = get_current_leave_period_dates(today)
    leave_period_start = period[0]
    leave_period_end = period[1]

    # Historical run: from April (leave period start) to today
    historical_start = leave_period_start
    historical_end = today

    print("\n" + "="*70)
    print("STARTING HISTORICAL CL ALLOCATION")
    print("="*70)
    print("Period: " + str(historical_start) + " to " + str(historical_end))
    print("="*70 + "\n")

    # Get all months from April to current month
    all_months = get_all_months_between(historical_start, historical_end)

    print("Total months to process: " + str(len(all_months)))

    # Find all employees whose probation ended
    employees = frappe.get_all("Employee",
        filters={
            "status": "Active",
            "custom_probation_end_date": ["is", "set"],
            "custom_probation_end_date": ["<", today]
        },
        fields=["name", "employee_name", "custom_probation_end_date"]
    )

    print("Found " + str(len(employees)) + " employees eligible for CL check\n")

    allocation_count = 0
    failed_count = 0
    skipped_count = 0

    for emp in employees:
        try:
            probation_end = frappe.utils.getdate(emp.custom_probation_end_date)
            
            # Get CL start date for this employee
            cl_start_date = get_cl_start_date(probation_end, leave_period_start)
            
            print("\n" + "-"*70)
            print("Processing: " + str(emp.employee_name) + " (" + str(emp.name) + ")")
            print("Probation End: " + str(probation_end) + " | CL Start: " + str(cl_start_date))
            print("-"*70)
            
            emp_allocation_count = 0
            emp_skipped_count = 0
            
            # Loop through all months
            for month in all_months:
                month_start = month[0]
                month_end = month[1]
                current_month = month_start.month
                
                # Skip if month is February or April
                if not should_allocate_cl_this_month(current_month):
                    emp_skipped_count = emp_skipped_count + 1
                    continue
                
                # Skip if month is before employee's CL start date
                if month_start < cl_start_date:
                    emp_skipped_count = emp_skipped_count + 1
                    continue
                
                # Skip if month is after leave period end
                if month_start > leave_period_end:
                    emp_skipped_count = emp_skipped_count + 1
                    continue
                
                # Check if CL already allocated for this month
                already_allocated = get_cl_allocation_for_month(emp.name, month_start, month_end)
                
                if already_allocated:
                    print("  " + format_month_year(month_start) + ": Already allocated")
                    emp_skipped_count = emp_skipped_count + 1
                else:
                    print("  " + format_month_year(month_start) + ": Allocating...")
                    # Allocate 1 CL for this month
                    success = allocate_monthly_cl_direct(
                        employee=emp.name,
                        month_start=month_start,
                        month_end=month_end
                    )
                    
                    if success:
                        allocation_count = allocation_count + 1
                        emp_allocation_count = emp_allocation_count + 1
                    else:
                        failed_count = failed_count + 1
            
            skipped_count = skipped_count + emp_skipped_count
            print("Summary: " + str(emp_allocation_count) + " created, " + str(emp_skipped_count) + " skipped")
            
        except Exception as e:
            error_msg = "EMPLOYEE ERROR: " + str(emp.name) + " - " + str(e)
            print(error_msg)
            frappe.log_error(message=str(e), title="Employee Processing Error - " + str(emp.name))
            failed_count = failed_count + 1
            continue

    print("\n" + "="*70)
    print("HISTORICAL CL ALLOCATION COMPLETED")
    print("="*70)
    print("Total allocations created: " + str(allocation_count))
    print("Total skipped: " + str(skipped_count))
    print("Total failed: " + str(failed_count))
    print("="*70 + "\n")

except Exception as e:
    print("CRITICAL ERROR IN MAIN EXECUTION: " + str(e))
    frappe.log_error(message=str(e), title="CL Allocation Script - Critical Error")
