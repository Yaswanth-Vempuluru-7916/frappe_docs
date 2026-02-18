MAX_CASUAL_LEAVE_PER_MONTH = 2

# Skip all validations for Administrator
if frappe.session.user != "Administrator":
    # Only apply validations for Casual Leave
    if doc.leave_type == "Casual Leave" and doc.status in ["Open","Approved"]:
        
        from_date = frappe.utils.getdate(doc.from_date)
        to_date = frappe.utils.getdate(doc.to_date)
        
        # ===== VALIDATION 1: Block February & May (except Primary/Secondary staff) =====
        # Get employee's staff category
        employee_staff_category = frappe.db.get_value("Employee", doc.employee, "custom_staff_category")
        
        # Only block if staff category is NOT Primary
        if employee_staff_category not in ["Primary"]:
            temp_date = from_date
            while temp_date <= to_date:
                if temp_date.month in [2, 5]:  # February or May
                    frappe.throw(_("Casual Leave cannot be applied in February and May."))
                temp_date = frappe.utils.add_days(temp_date, 1)
        
        
        # ===== VALIDATION 2: Holiday Prefix/Suffix Check =====
        # Get employee's holiday list
        employee_holiday_list = frappe.db.get_value("Employee", doc.employee, "holiday_list")
        
        if not employee_holiday_list:
            frappe.throw(_("No holiday list is assigned to your profile. Contact HR."))
        
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
            # Check previous day (prefix)
            previous_day = frappe.utils.add_days(temp_date, -1)
            if previous_day in holiday_dates:
                frappe.throw(_(f"Casual Leave cannot be applied as {frappe.utils.formatdate(previous_day, 'dd-MM-yyyy')} (previous day) is a holiday. Apply for LOP."))
            
            # Check next day (suffix)
            next_day = frappe.utils.add_days(temp_date, 1)
            if next_day in holiday_dates:
                frappe.throw(_(f"Casual Leave cannot be applied as {frappe.utils.formatdate(next_day, 'dd-MM-yyyy')} (next day) is a holiday. Apply for LOP."))
            
            temp_date = frappe.utils.add_days(temp_date, 1)
            
        # ===== VALIDATION 2.1: Stayback Day Restriction (No strftime) =====

        # Fetch employee stayback day (e.g., Monday, Tuesday, etc.)
        stayback_day = frappe.db.get_value("Employee", doc.employee, "custom_stayback_day")
        
        if stayback_day:
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
            temp_date = from_date
            while temp_date <= to_date:
        
                # Convert weekday index -> weekday name
                weekday_name = day_names[temp_date.weekday()]
        
                if weekday_name == stayback_day:
                    frappe.throw(_(
                        f"Casual Leave cannot be applied on "
                        f"{frappe.utils.formatdate(temp_date, 'dd-MM-yyyy')} "
                        f"because {stayback_day} is your assigned Stayback Day. "
                        f"Apply for LOP instead."
                    ))
        
                temp_date = frappe.utils.add_days(temp_date, 1)
        
        # ===== VALIDATION 3: Monthly 2-Day Limit (Handle Cross-Month Applications) =====
        # Calculate total days in current application
        current_application_days = frappe.utils.date_diff(to_date, from_date) + 1
        
        # Handle half day leaves
        if doc.half_day:
            current_application_days -= 0.5
        
        # Check if leave spans multiple months
        if from_date.month != to_date.month or from_date.year != to_date.year:
            # For cross-month applications, split the validation by month
            temp_date = from_date
            months_to_check = []
            
            while temp_date <= to_date:
                month_year_key = (temp_date.month, temp_date.year)
                if month_year_key not in months_to_check:
                    months_to_check.append(month_year_key)
                temp_date = frappe.utils.add_days(temp_date, 1)
            
            # Validate each month separately
            for month, year in months_to_check:
                # Count days in this specific month for current application
                current_month_days = 0
                temp_date = from_date
                while temp_date <= to_date:
                    if temp_date.month == month and temp_date.year == year:
                        current_month_days += 1
                    temp_date = frappe.utils.add_days(temp_date, 1)
                
                # Adjust for half day if applicable
                if doc.half_day:
                    half_day_date = frappe.utils.getdate(doc.half_day_date) if doc.half_day_date else from_date
                    if half_day_date.month == month and half_day_date.year == year:
                        current_month_days -= 0.5
                
                # Calculate first and last day of the target month for comparison
                first_day_of_month = frappe.utils.getdate(f"{year}-{month:02d}-01")
                last_day_of_month = frappe.utils.get_last_day(first_day_of_month)
                
                # Query existing approved/submitted Casual Leave in this specific month
                # FIXED: Now catches leaves that span across the month (like Dec 30 -> Feb 2)
                existing_leaves = frappe.db.sql("""
                    SELECT name, from_date, to_date, half_day, half_day_date, total_leave_days
                    FROM `tabLeave Application`
                    WHERE employee = %s
                    AND leave_type = 'Casual Leave'
                    AND docstatus IN (0, 1)
                    AND status IN ('Approved', 'Open')
                    AND name != %s
                    AND (
                        (MONTH(from_date) = %s AND YEAR(from_date) = %s)
                        OR (MONTH(to_date) = %s AND YEAR(to_date) = %s)
                        OR (from_date < %s AND to_date > %s)
                    )
                """, (doc.employee, doc.name, month, year, month, year, 
                      first_day_of_month, last_day_of_month), as_dict=1)
                
                # Calculate total days already taken in this month
                total_days_in_month = 0
                for leave in existing_leaves:
                    leave_from = frappe.utils.getdate(leave.from_date)
                    leave_to = frappe.utils.getdate(leave.to_date)
                    
                    # Count only days that fall in the current month being checked
                    temp_date = leave_from
                    month_specific_days = 0
                    while temp_date <= leave_to:
                        if temp_date.month == month and temp_date.year == year:
                            month_specific_days += 1
                        temp_date = frappe.utils.add_days(temp_date, 1)
                    
                    # Adjust for half day
                    if leave.half_day:
                        half_day_date = frappe.utils.getdate(leave.half_day_date) if leave.half_day_date else leave_from
                        if half_day_date.month == month and half_day_date.year == year:
                            month_specific_days -= 0.5
                    
                    total_days_in_month += month_specific_days
                
                # Format the number to show decimals only when needed
                formatted_days = int(total_days_in_month) if total_days_in_month == int(total_days_in_month) else total_days_in_month
                formatted_current = int(current_month_days) if current_month_days == int(current_month_days) else current_month_days
                
                month_name = frappe.utils.formatdate(frappe.utils.getdate(f"{year}-{month:02d}-01"), "MMMM yyyy")
                
                # Validate for this specific month
                if total_days_in_month == 0 and current_month_days > MAX_CASUAL_LEAVE_PER_MONTH:
                    frappe.throw(_(f"You cannot apply for {formatted_current} days of Casual Leave in {month_name}. Maximum allowed is {MAX_CASUAL_LEAVE_PER_MONTH} days per month."))
                
                if total_days_in_month >= MAX_CASUAL_LEAVE_PER_MONTH:
                    frappe.throw(_(f"You have already used {formatted_days} day(s) of Casual Leave in {month_name}. No further Casual Leave can be applied."))
                    
                if total_days_in_month + current_month_days > MAX_CASUAL_LEAVE_PER_MONTH:
                    remaining = MAX_CASUAL_LEAVE_PER_MONTH - total_days_in_month
                    formatted_remaining = int(remaining) if remaining == int(remaining) else remaining
                    frappe.throw(_(f"You have already used {formatted_days} day(s) of Casual Leave in {month_name}. You can only apply for {formatted_remaining} more day(s). The monthly limit is {MAX_CASUAL_LEAVE_PER_MONTH} days."))
        
        else:
            # Single month application
            application_month = from_date.month
            application_year = from_date.year
            
            # Calculate first and last day of the target month for comparison
            first_day_of_month = frappe.utils.getdate(f"{application_year}-{application_month:02d}-01")
            last_day_of_month = frappe.utils.get_last_day(first_day_of_month)
            
            # Query existing approved/submitted Casual Leave in the same month
            # FIXED: Now catches leaves that span across the month (like Dec 30 -> Feb 2)
            existing_leaves = frappe.db.sql("""
                SELECT name, from_date, to_date, half_day, half_day_date, total_leave_days
                FROM `tabLeave Application`
                WHERE employee = %s
                AND leave_type = 'Casual Leave'
                AND docstatus IN (0, 1)
                AND status IN ('Approved', 'Open')
                AND name != %s
                AND (
                    (YEAR(from_date) = %s AND MONTH(from_date) = %s)
                    OR (YEAR(to_date) = %s AND MONTH(to_date) = %s)
                    OR (from_date < %s AND to_date > %s)
                )
            """, (doc.employee, doc.name, application_year, application_month, 
                  application_year, application_month, first_day_of_month, last_day_of_month), as_dict=1)
            
            # Calculate total days already taken in the month
            total_days_in_month = 0
            for leave in existing_leaves:
                leave_from = frappe.utils.getdate(leave.from_date)
                leave_to = frappe.utils.getdate(leave.to_date)
                
                # Count only days that fall in the application month
                temp_date = leave_from
                month_specific_days = 0
                while temp_date <= leave_to:
                    if temp_date.month == application_month and temp_date.year == application_year:
                        month_specific_days += 1
                    temp_date = frappe.utils.add_days(temp_date, 1)
                
                # Adjust for half day
                if leave.half_day:
                    half_day_date = frappe.utils.getdate(leave.half_day_date) if leave.half_day_date else leave_from
                    if half_day_date.month == application_month and half_day_date.year == application_year:
                        month_specific_days -= 0.5
                
                total_days_in_month += month_specific_days
                    
            # Format the number to show decimals only when needed
            formatted_days = int(total_days_in_month) if total_days_in_month == int(total_days_in_month) else total_days_in_month
            formatted_current = int(current_application_days) if current_application_days == int(current_application_days) else current_application_days
            
            # Case 1: No previous leave, but current application itself exceeds limit
            if total_days_in_month == 0 and current_application_days > MAX_CASUAL_LEAVE_PER_MONTH:
                frappe.throw(_(f"You cannot apply for {formatted_current} days of Casual Leave in a month. Maximum allowed is {MAX_CASUAL_LEAVE_PER_MONTH} days per month."))
            
            # Case 2: Previous leaves already consumed full quota
            if total_days_in_month >= MAX_CASUAL_LEAVE_PER_MONTH:
                frappe.throw(_(f"You have already used {formatted_days} day(s) of Casual Leave this month. No further Casual Leave can be applied."))
                
            # Case 3: Combination exceeds limit
            if total_days_in_month + current_application_days > MAX_CASUAL_LEAVE_PER_MONTH:
                remaining = MAX_CASUAL_LEAVE_PER_MONTH - total_days_in_month
                formatted_remaining = int(remaining) if remaining == int(remaining) else remaining
                frappe.throw(_(f"You have already used {formatted_days} day(s) of Casual Leave this month. You can only apply for {formatted_remaining} more day(s). The monthly limit is {MAX_CASUAL_LEAVE_PER_MONTH} days."))
