

# Skip all validations for Administrator
if frappe.session.user != "Administrator":
    
    # Only apply validations for Casual Leave
    if doc.leave_type == "Casual Leave":
        
        from_date = frappe.utils.getdate(doc.from_date)
        to_date = frappe.utils.getdate(doc.to_date)
        
        # ===== VALIDATION 1: Block February & May =====
        temp_date = from_date
        while temp_date <= to_date:
            if temp_date.month in [2, 5]:  # February or May
                frappe.throw(_("Casual Leave cannot be applied in February and May."))
            temp_date = frappe.utils.add_days(temp_date, 1)
        
        
        # ===== VALIDATION 2: Holiday Prefix/Suffix Check =====
        # Get employee's holiday list
        employee_holiday_list = frappe.db.get_value("Employee", doc.employee, "holiday_list")
        
        if not employee_holiday_list:
            frappe.throw(_("No holiday list assigned to employee. Please contact HR."))
        
        # Fetch all holidays from the employee's holiday list
        holidays = frappe.db.sql("""
            SELECT holiday_date 
            FROM `tabHoliday` 
            WHERE parent = %s
        """, (employee_holiday_list,), as_dict=1)
        
        # Create a set of holiday dates for quick lookup
        holiday_dates = {frappe.utils.getdate(h.holiday_date) for h in holidays}
        
        # Check each day in the leave application
        temp_date = from_date
        while temp_date <= to_date:
            # Check if this is a half day - only check if it's a full day leave
            # Skip weekends if needed (optional - depends on your half_day logic)
            
            # Check previous day (prefix)
            previous_day = frappe.utils.add_days(temp_date, -1)
            if previous_day in holiday_dates:
                frappe.throw(_(f"The previous day {frappe.utils.formatdate(previous_day, 'dd-MM-yyyy')} is a holiday. Apply for LOP instead."))
            
            # Check next day (suffix)
            next_day = frappe.utils.add_days(temp_date, 1)
            if next_day in holiday_dates:
                frappe.throw(_(f"The next day {frappe.utils.formatdate(next_day, 'dd-MM-yyyy')} is a holiday. Apply for LOP instead."))
            
            temp_date = frappe.utils.add_days(temp_date, 1)
        
        
        # ===== VALIDATION 3: Monthly 2-Day Limit =====
        # Get the month and year of the application
        application_month = from_date.month
        application_year = from_date.year
        
        # Calculate total days in current application
        current_application_days = frappe.utils.date_diff(to_date, from_date) + 1
        
        # Handle half day leaves
        if doc.half_day:
            current_application_days = 0.5
        
        # Query existing approved/submitted Casual Leave in the same month
        existing_leaves = frappe.db.sql("""
            SELECT name, from_date, to_date, half_day, total_leave_days
            FROM `tabLeave Application`
            WHERE employee = %s
            AND leave_type = 'Casual Leave'
            AND docstatus = 1
            AND name != %s
            AND (
                (MONTH(from_date) = %s AND YEAR(from_date) = %s)
                OR (MONTH(to_date) = %s AND YEAR(to_date) = %s)
            )
        """, (doc.employee, doc.name, application_month, application_year, 
              application_month, application_year), as_dict=1)
        
        # Calculate total days already taken in the month
        total_days_in_month = 0
        for leave in existing_leaves:
            # Use total_leave_days field if available, otherwise calculate
            if leave.total_leave_days:
                total_days_in_month += leave.total_leave_days
            else:
                leave_days = frappe.utils.date_diff(frappe.utils.getdate(leave.to_date), frappe.utils.getdate(leave.from_date)) + 1
                if leave.half_day:
                    leave_days = 0.5
                total_days_in_month += leave_days
        
        # Check if adding current application exceeds 2 days
        if total_days_in_month + current_application_days > 2:
            frappe.throw(_(f"You have already availed {total_days_in_month} day(s) of Casual Leave this month. Maximum limit is 2 days per month."))
