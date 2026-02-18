MAX_CASUAL_LEAVE_PER_MONTH = 2

if frappe.session.user != "Administrator":
    if doc.leave_type == "Casual Leave" and doc.status in ["Open", "Approved"]:

        from_date = frappe.utils.getdate(doc.from_date)
        to_date = frappe.utils.getdate(doc.to_date)

        # ============================================================
        # HELPER: Resolve holiday list per date (Assignment Aware)
        # ============================================================
        def get_holiday_list_for_date(employee, date):
            assignment = frappe.db.sql("""
                SELECT hla.holiday_list
                FROM `tabHoliday List Assignment` hla
                INNER JOIN `tabHoliday List` hl
                    ON hla.holiday_list = hl.name
                WHERE hla.assigned_to = %s
                AND hla.docstatus = 1
                AND %s BETWEEN hl.from_date AND hl.to_date
                ORDER BY hl.from_date DESC
                LIMIT 1
            """, (employee, date), as_dict=1)

            if assignment:
                return assignment[0]["holiday_list"]

            fallback = frappe.db.get_value("Employee", employee, "holiday_list")
            if fallback:
                validity = frappe.db.get_value(
                    "Holiday List",
                    fallback,
                    ["from_date", "to_date"],
                    as_dict=1
                )
                if validity and validity.from_date <= date <= validity.to_date:
                    return fallback

            frappe.throw(_(
                f"No Holiday List is assigned for "
                f"{frappe.utils.formatdate(date, 'dd-MM-yyyy')}. "
                f"Please assign a valid Holiday List to the employee before applying leave."
            ))

        # ============================================================
        # VALIDATION 1: February & May Restriction
        # ============================================================
        employee_staff_category = frappe.db.get_value(
            "Employee", doc.employee, "custom_staff_category"
        )

        if employee_staff_category not in ["Primary"]:
            temp_date = from_date
            while temp_date <= to_date:
                if temp_date.month in [2, 5]:
                    frappe.throw(_("Casual Leave cannot be applied in February and May."))
                temp_date = frappe.utils.add_days(temp_date, 1)

        # ============================================================
        # PREFIX / SUFFIX CHECK (ASSIGNMENT AWARE)
        # ============================================================
        temp_date = from_date
        while temp_date <= to_date:

            previous_day = frappe.utils.add_days(temp_date, -1)
            prev_list = get_holiday_list_for_date(doc.employee, previous_day)

            if prev_list and frappe.db.exists(
                "Holiday",
                {"parent": prev_list, "holiday_date": previous_day}
            ):
                frappe.throw(_(
                    f"Casual Leave cannot be applied as "
                    f"{frappe.utils.formatdate(previous_day, 'dd-MM-yyyy')} "
                    f"(previous day) is a holiday. Apply for LOP."
                ))

            next_day = frappe.utils.add_days(temp_date, 1)
            next_list = get_holiday_list_for_date(doc.employee, next_day)

            if next_list and frappe.db.exists(
                "Holiday",
                {"parent": next_list, "holiday_date": next_day}
            ):
                frappe.throw(_(
                    f"Casual Leave cannot be applied as "
                    f"{frappe.utils.formatdate(next_day, 'dd-MM-yyyy')} "
                    f"(next day) is a holiday. Apply for LOP."
                ))

            temp_date = frappe.utils.add_days(temp_date, 1)

        # ============================================================
        # STAYBACK CHECK
        # ============================================================
        stayback_day = frappe.db.get_value(
            "Employee", doc.employee, "custom_stayback_day"
        )

        if stayback_day:
            day_names = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

            temp_date = from_date
            while temp_date <= to_date:
                weekday_name = day_names[temp_date.weekday()]
                if weekday_name == stayback_day:
                    frappe.throw(_(
                        f"Casual Leave cannot be applied on "
                        f"{frappe.utils.formatdate(temp_date, 'dd-MM-yyyy')} "
                        f"because {stayback_day} is your assigned Stayback Day. "
                        f"Apply for LOP instead."
                    ))
                temp_date = frappe.utils.add_days(temp_date, 1)

        # ============================================================
        # MONTHLY LIMIT (UNIFIED, HOLIDAY + ASSIGNMENT AWARE)
        # ============================================================

        # Collect months involved in current application
        months_to_check = []
        temp_date = from_date
        while temp_date <= to_date:
            key = (temp_date.month, temp_date.year)
            if key not in months_to_check:
                months_to_check.append(key)
            temp_date = frappe.utils.add_days(temp_date, 1)

        for month, year in months_to_check:

            # --------------------------------------------------------
            # Count working days in CURRENT application for this month
            # --------------------------------------------------------
            current_month_days = 0
            temp_date = from_date

            while temp_date <= to_date:
                if temp_date.month == month and temp_date.year == year:
                    holiday_list = get_holiday_list_for_date(doc.employee, temp_date)

                    is_holiday = False
                    if holiday_list:
                        is_holiday = frappe.db.exists(
                            "Holiday",
                            {"parent": holiday_list, "holiday_date": temp_date}
                        )

                    if not is_holiday:
                        current_month_days += 1

                temp_date = frappe.utils.add_days(temp_date, 1)

            if doc.half_day:
                half_day_date = frappe.utils.getdate(doc.half_day_date) if doc.half_day_date else from_date
                if half_day_date.month == month and half_day_date.year == year:
                    if current_month_days > 0:
                        current_month_days -= 0.5

            # --------------------------------------------------------
            # Fetch existing leaves overlapping this month
            # --------------------------------------------------------
            first_day = frappe.utils.getdate(f"{year}-{month:02d}-01")
            last_day = frappe.utils.get_last_day(first_day)

            existing_leaves = frappe.db.sql("""
                SELECT name, from_date, to_date, half_day, half_day_date
                FROM `tabLeave Application`
                WHERE employee = %s
                AND leave_type = 'Casual Leave'
                AND docstatus IN (0,1)
                AND status IN ('Approved','Open')
                AND name != %s
                AND (
                    (from_date <= %s AND to_date >= %s)
                )
            """, (doc.employee, doc.name, last_day, first_day), as_dict=1)

            total_days_in_month = 0

            for leave in existing_leaves:
                leave_from = frappe.utils.getdate(leave.from_date)
                leave_to = frappe.utils.getdate(leave.to_date)

                temp_date = leave_from
                while temp_date <= leave_to:
                    if temp_date.month == month and temp_date.year == year:

                        holiday_list = get_holiday_list_for_date(doc.employee, temp_date)

                        is_holiday = False
                        if holiday_list:
                            is_holiday = frappe.db.exists(
                                "Holiday",
                                {"parent": holiday_list, "holiday_date": temp_date}
                            )

                        if not is_holiday:
                            total_days_in_month += 1

                    temp_date = frappe.utils.add_days(temp_date, 1)

                if leave.half_day:
                    half_day_date = frappe.utils.getdate(leave.half_day_date) if leave.half_day_date else leave_from
                    if half_day_date.month == month and half_day_date.year == year:
                        if total_days_in_month > 0:
                            total_days_in_month -= 0.5

            # --------------------------------------------------------
            # FINAL VALIDATION
            # --------------------------------------------------------
            if total_days_in_month >= MAX_CASUAL_LEAVE_PER_MONTH:
                frappe.throw(_(
                    f"You have already used {total_days_in_month} day(s) of Casual Leave in "
                    f"{frappe.utils.formatdate(first_day, 'MMMM yyyy')}. "
                    f"No further Casual Leave can be applied."
                ))

            if total_days_in_month + current_month_days > MAX_CASUAL_LEAVE_PER_MONTH:
                remaining = MAX_CASUAL_LEAVE_PER_MONTH - total_days_in_month
                frappe.throw(_(
                    f"You have already used {total_days_in_month} day(s) of Casual Leave in "
                    f"{frappe.utils.formatdate(first_day, 'MMMM yyyy')}. "
                    f"You can only apply for {remaining} more day(s). "
                    f"The monthly limit is {MAX_CASUAL_LEAVE_PER_MONTH} days."
                ))
