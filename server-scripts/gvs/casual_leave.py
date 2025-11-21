# Server Script: Historical CL Backfill with Cumulative Balance
# Run this ONCE to backfill all historical allocations

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

def get_months_between(start_date, end_date):
    """Get all months between start and end date"""
    months = []
    current = frappe.utils.get_first_day(start_date)
    
    while current <= end_date:
        if should_allocate_cl_this_month(current.month):
            month_start = frappe.utils.get_first_day(current)
            month_end = frappe.utils.get_last_day(current)
            months.append((month_start, month_end))
        current = frappe.utils.add_months(current, 1)
    
    return months

def calculate_leaves_taken_in_period(employee, from_date, to_date):
    """Calculate total leaves taken in a period"""
    leaves_taken = frappe.db.sql("""
        SELECT COALESCE(SUM(total_leave_days), 0) as taken
        FROM `tabLeave Application`
        WHERE employee = %s
        AND leave_type = 'Casual Leave'
        AND docstatus = 1
        AND from_date <= %s
        AND to_date >= %s
    """, (employee, to_date, from_date))[0][0]
    
    return float(leaves_taken)

def cancel_existing_allocations(employee, leave_period_start):
    """Cancel all existing CL allocations for employee in current period"""
    existing = frappe.get_all("Leave Allocation",
        filters={
            "employee": employee,
            "leave_type": "Casual Leave",
            "from_date": [">=", leave_period_start],
            "docstatus": 1
        },
        fields=["name"]
    )
    
    for alloc in existing:
        try:
            doc = frappe.get_doc("Leave Allocation", alloc.name)
            doc.cancel()
            frappe.delete_doc("Leave Allocation", alloc.name)
            print("  Cancelled old allocation: " + alloc.name)
        except Exception as e:
            print("  Error cancelling " + alloc.name + ": " + str(e))

def create_cumulative_allocations(employee, months, employee_name):
    """Create cumulative allocations for all months"""
    cumulative_unused = 0
    allocation_count = 0
    
    for month in months:
        month_start = month[0]
        month_end = month[1]
        
        try:
            # Calculate leaves taken in this specific month
            leaves_taken_this_month = calculate_leaves_taken_in_period(
                employee, month_start, month_end
            )
            
            # New allocation for this month
            new_leaves = 1
            total_leaves = new_leaves + cumulative_unused
            
            # Create allocation
            doc = frappe.get_doc({
                "doctype": "Leave Allocation",
                "employee": employee,
                "leave_type": "Casual Leave",
                "from_date": month_start,
                "to_date": month_end,
                "new_leaves_allocated": new_leaves,
                "total_leaves_allocated": total_leaves,
                "unused_leaves": cumulative_unused
            })
            
            doc.insert(ignore_permissions=True, ignore_mandatory=True)
            doc.submit()
            frappe.db.commit()
            
            # Calculate unused for next month
            used_from_this_allocation = min(leaves_taken_this_month, total_leaves)
            cumulative_unused = total_leaves - used_from_this_allocation
            
            month_name = month_start.strftime("%b %Y")
            print("  " + month_name + ": Total=" + str(total_leaves) + 
                  " | Used=" + str(used_from_this_allocation) + 
                  " | Carried=" + str(cumulative_unused))
            
            allocation_count = allocation_count + 1
            
        except Exception as e:
            print("  ERROR for " + month_start.strftime("%b %Y") + ": " + str(e))
            frappe.db.rollback()
            continue
    
    return allocation_count

# ==================== MAIN EXECUTION ====================

try:
    today = frappe.utils.getdate()
    
    # Get current leave period
    period = get_current_leave_period_dates(today)
    leave_period_start = period[0]
    leave_period_end = period[1]
    
    print("\n" + "="*70)
    print("HISTORICAL CL BACKFILL (CUMULATIVE)")
    print("="*70)
    print("Period: " + str(leave_period_start) + " to " + str(today))
    print("="*70 + "\n")
    
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
    
    total_allocations = 0
    
    for emp in employees:
        try:
            probation_end = frappe.utils.getdate(emp.custom_probation_end_date)
            cl_start_date = get_cl_start_date(probation_end, leave_period_start)
            
            print("\n" + "-"*70)
            print("Employee: " + str(emp.employee_name) + " (" + str(emp.name) + ")")
            print("Probation End: " + str(probation_end) + " | CL Start: " + str(cl_start_date))
            print("-"*70)
            
            # Get all eligible months
            months = get_months_between(cl_start_date, today)
            
            if not months:
                print("No eligible months found")
                continue
            
            print("Processing " + str(len(months)) + " months...")
            
            # Cancel existing allocations first
            print("\nCancelling existing allocations...")
            cancel_existing_allocations(emp.name, leave_period_start)
            
            # Create new cumulative allocations
            print("\nCreating cumulative allocations...")
            count = create_cumulative_allocations(emp.name, months, emp.employee_name)
            
            total_allocations = total_allocations + count
            print("\n✓ Created " + str(count) + " allocations")
            
        except Exception as e:
            print("ERROR processing employee: " + str(e))
            frappe.log_error(message=str(e), title="Backfill Error - " + str(emp.name))
            continue
    
    print("\n" + "="*70)
    print("BACKFILL COMPLETED")
    print("="*70)
    print("Total allocations created: " + str(total_allocations))
    print("="*70 + "\n")

except Exception as e:
    print("CRITICAL ERROR: " + str(e))
    frappe.log_error(message=str(e), title="CL Backfill - Critical Error")
