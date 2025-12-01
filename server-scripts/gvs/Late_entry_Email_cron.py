def execute():
    print("=" * 70)
    print("STARTING LATE ENTRY HALF DAY MASS CHECK WITH ABSENT ON 4th HALF DAY (SAFE EXEC INDEX FIX)")
    print("=" * 70)
    today = frappe.utils.getdate("2025-11-28")
    month_start = today.replace(day=1)
    print(f"Period: {month_start} to {today} (including today)")
    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "user_id", "company_email"]
    )
    print(f"Found {len(employees)} employees for late entry correction")
    modified_count = 0
    skipped = 0

    for emp in employees:
        print("-" * 70)
        print(f"Processing: {emp.get('employee_name')} ({emp.get('name')})")
        try:
            marked = correct_late_half_days_with_absent(emp, month_start, today)
            modified_count += marked
            print(f"Attendance changes for Late Entry: {marked}")
        except Exception as e:
            skipped += 1
            frappe.log_error(
                title=f"Late Entry Processing Exception for Employee {emp.get('name')}",
                message=str(e)
            )
            print(f"FAILED: {emp.get('employee_name')} ({emp.get('name')}) - {str(e)}")
    print("=" * 70)
    print("LATE ENTRY MASS CHECK COMPLETED")
    print("=" * 70)
    print(f"Attendance updated: {modified_count}, Skipped: {skipped}")

def correct_late_half_days_with_absent(emp, month_start, until_date):
    employee_id = emp.name
    employee_name = emp.employee_name or employee_id

    shift_doc = get_employee_shift(employee_id, until_date)
    if not shift_doc or not shift_doc.start_time:
        print(f"SKIPPED: No shift or start time for {employee_name}")
        return 0

    try:
        late_grace_minutes = shift_doc.late_entry_grace_period
    except Exception:
        late_grace_minutes = 10

    shift_start = shift_doc.start_time
    print(f"Shift Start: {shift_start}, Grace Period: {late_grace_minutes} mins")

    checkins = get_employee_checkins_for_month(employee_id, month_start, until_date)
    print(f"Total check-ins found: {len(checkins)}")
    late_days = get_late_days_from_checkins(checkins, shift_start, late_grace_minutes)
    sorted_dates = sorted(late_days.keys())
    month_late_dates = []
    for d in sorted_dates:
        if late_days[d]["is_late"] and d <= str(until_date):
            month_late_dates.append(d)

    changes = 0
    i = 0
    while i < len(month_late_dates):
        day = month_late_dates[i]
        late_num = i + 1
        if late_num >= 4:  # 4th late and beyond
            print(f"Checking {day} (Late #{late_num})...")
            att_rec = get_attendance_record(employee_id, day)
            att_name = att_rec[0]
            att_status = att_rec[1]
            try:
                if att_status == "Absent":
                    print(f"-- Already Absent on {day}, SKIP.")
                    i += 1
                    continue
                elif att_status == "Half Day":
                    change_attendance_status(employee_id, employee_name, day, shift_doc.name, "Absent", late_num, late_days[day]["first_in"])
                    print(f"-- Marked Absent (was Half Day) on {day}")
                    changes += 1
                else:
                    change_attendance_status(employee_id, employee_name, day, shift_doc.name, "Half Day", late_num, late_days[day]["first_in"])
                    print(f"-- Marked Half Day on {day}")
                    changes += 1
            except Exception as e:
                frappe.log_error(
                    title=f"Attendance Change Error: {employee_id} ({day})",
                    message=str(e)
                )
                print(f"ERROR changing attendance for {employee_name} on {day} - {str(e)}")
        i += 1
    return changes

def get_attendance_record(employee_id, att_date):
    att = frappe.get_all(
        "Attendance",
        filters={
            "employee": employee_id,
            "attendance_date": att_date,
            "docstatus": 1
        },
        fields=["name", "status"]
    )
    if att:
        return [att[0]["name"], att[0]["status"]]
    return [None, None]

def change_attendance_status(employee_id, employee_name, attendance_date, shift_name, new_status, late_number, checkin_time):
    print(f"Updating attendance on {attendance_date} to {new_status}")
    att_rec = get_attendance_record(employee_id, attendance_date)
    att_name = att_rec[0]
    old_status = att_rec[1]
    if att_name:
        att = frappe.get_doc("Attendance", att_name)
        print(f"Found old attendance {att_name} status {old_status}")
        if att.docstatus == 1:
            att.flags.ignore_permissions = True
            att.cancel()
        att.delete()
        print(f"Deleted old attendance {att_name}")
    att = frappe.new_doc("Attendance")
    att.employee = employee_id
    att.employee_name = employee_name
    att.attendance_date = attendance_date
    att.company = frappe.db.get_value("Employee", employee_id, "company")
    att.shift = shift_name
    att.status = new_status
    att.flags.ignore_permissions = True
    att.save()
    att.submit()
    checkin_str = str(checkin_time)[11:16] if checkin_time else "-"
    comment_text = (
        f"Marked {new_status} automatically on {attendance_date} due to late entry number {late_number} of month. "
        f"First check-in: {checkin_str}."
    )
    att.add_comment("Comment", comment_text)
    frappe.get_doc("Employee", employee_id).add_comment("Comment", comment_text)
    print(f"Attendance marked {new_status} and commented for {employee_name} on {attendance_date} (Late #{late_number})")

def get_employee_shift(employee_id, on_date):
    try:
        shift_assignment = frappe.db.sql(
            """
            SELECT sa.shift_type AS shift
            FROM `tabShift Assignment` sa
            WHERE sa.employee = %s
              AND sa.docstatus = 1
              AND sa.start_date <= %s
              AND (sa.end_date IS NULL OR sa.end_date >= %s)
            ORDER BY sa.start_date DESC
            LIMIT 1
            """,
            (employee_id, on_date, on_date),
            as_dict=1,
        )
        shift_name = None
        if shift_assignment:
            shift_name = shift_assignment[0].get("shift")
        if not shift_name:
            shift_name = frappe.db.get_value("Employee", employee_id, "default_shift")
        if not shift_name:
            return None
        return frappe.get_doc("Shift Type", shift_name)
    except Exception as e:
        frappe.log_error(
            title=f"Shift Lookup Exception: {employee_id}",
            message=str(e)
        )
        print(f"ERROR finding shift for {employee_id} - {str(e)}")
        return None

def get_employee_checkins_for_month(employee_id, month_start, until_date):
    try:
        end_bound = frappe.utils.add_days(until_date, 1)
        checkins = frappe.get_all(
            "Employee Checkin",
            filters={
                "employee": employee_id,
                "time": ["between", [month_start, end_bound]],
                "log_type": "IN",
            },
            fields=["name", "time"],
            order_by="time asc",
        )
        return checkins
    except Exception as e:
        frappe.log_error(
            title=f"Checkin Fetch Exception: {employee_id}",
            message=str(e)
        )
        print(f"ERROR fetching checkins for {employee_id} - {str(e)}")
        return []

def get_late_days_from_checkins(checkins, shift_start, late_grace_minutes):
    per_day_first_in = {}
    for ch in checkins:
        ch_time = str(ch["time"])
        ch_date = ch_time[:10]
        if ch_date not in per_day_first_in:
            per_day_first_in[ch_date] = []
        per_day_first_in[ch_date].append(ch_time)
    late_days = {}
    for day in per_day_first_in:
        times = per_day_first_in[day]
        times.sort()
        first_in = times[0]
        print(f"Check-ins for {day}:")
        for t in times:
            print(f"   - {t}")
        shift_hms = str(shift_start).split(":")
        shift_hour = int(shift_hms[0])
        shift_minute = int(shift_hms[1])
        allowed_minute = shift_minute + late_grace_minutes
        allowed_hour = shift_hour + allowed_minute // 60
        allowed_minute = allowed_minute % 60
        allowed_time = f"{allowed_hour:02d}:{allowed_minute:02d}"
        first_in_time = first_in[11:16]
        is_late = first_in_time > allowed_time
        print(f"Day: {day}, First In: {first_in_time}, Allowed: {allowed_time}, Late: {is_late}")
        late_days[day] = {
            "is_late": is_late,
            "first_in": first_in,
        }
    return late_days

execute()
