def execute():
    print("=" * 70)
    print("STARTING LATE ENTRY EMAIL/CHECK (EMAIL ONLY, Custom Template)")
    print("=" * 70)
    today = frappe.utils.getdate('2025-11-27')
    month_start = today.replace(day=1)

    print(f"Period: {month_start} to {today}")
    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "user_id", "company_email"]
    )
    print(f"Found {len(employees)} employees for late entry check")
    emails_sent = 0
    skipped = 0

    for emp in employees:
        print("-" * 70)
        print(f"Processing: {emp.get('employee_name')} ({emp.get('name')})")
        try:
            status = process_employee_late_entry_email_only(emp, month_start, today)
            if status == "late_email":
                emails_sent += 1
                print("SUCCESS: Email sent for Late Entry")
            else:
                print("SKIPPED: No action needed")
                skipped += 1
        except Exception as e:
            skipped += 1
            frappe.log_error(
                title=f"Late Entry Email Exception for Employee {emp.get('name')}",
                message=str(e)
            )
            print(f"FAILED: {emp.get('employee_name')} ({emp.get('name')}) - {str(e)}")

    print("=" * 70)
    print("LATE ENTRY EMAIL NOTIFICATION COMPLETED")
    print("=" * 70)
    print(f"Sent emails: {emails_sent}, Skipped: {skipped}")

def process_employee_late_entry_email_only(emp, month_start, today):
    employee_id = emp.name
    employee_name = emp.employee_name or employee_id
    employee_email = emp.user_id or emp.company_email
    if not employee_email:
        print(f"SKIPPED: Missing email for {employee_name} ({employee_id})")
        frappe.log_error(
            title=f"Missing Employee Email: {employee_id}",
            message=f"No user_id or company_email found for this employee: {employee_name} ({employee_id})"
        )
        return "skipped"

    shift_doc = get_employee_shift(employee_id, today)
    if not shift_doc or not shift_doc.start_time:
        print(f"SKIPPED: No shift/start time for {employee_name} ({employee_id})")
        return "skipped"

    try:
        late_grace_minutes = shift_doc.late_entry_grace_period
    except Exception:
        late_grace_minutes = 10

    shift_start = shift_doc.start_time
    print(f"Shift Start: {shift_start}, Grace Period: {late_grace_minutes} mins")

    checkins = get_employee_checkins_for_month(employee_id, month_start, today)
    print(f"Total check-ins found: {len(checkins)}")
    if checkins:
        print("All check-in times:")
        for ch in checkins:
            print(f"   - {str(ch['time'])}")

    late_days = get_late_days_from_checkins(checkins, shift_start, late_grace_minutes)
    sorted_dates = sorted([d for d in late_days.keys() if d <= str(today)])
    this_month_lates = [d for d in sorted_dates if late_days[d]["is_late"]]
    total_lates = len(this_month_lates)
    print(f"Total late days so far: {total_lates}")

    today_str = str(today)
    if today_str not in late_days or not late_days[today_str]["is_late"]:
        print(f"No late entry for {employee_name} today.")
        return "skipped"

    this_late_number = this_month_lates.index(today_str) + 1

    send_late_entry_email_with_template(
        employee_id=employee_id,
        employee_name=employee_name,
        employee_email=employee_email,
        attendance_date=today_str,
        shift_start=shift_start,
        first_in=late_days[today_str]["first_in"],
        current_late_number=this_late_number,
    )
    print(f"Email sent: {employee_name} ({employee_id}) - Late #{this_late_number}")
    return "late_email"

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

def get_employee_checkins_for_month(employee_id, month_start, today):
    try:
        end_bound = frappe.utils.add_days(today, 1)
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
    for day, times in per_day_first_in.items():
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

def send_late_entry_email_with_template(
    employee_id,
    employee_name,
    employee_email,
    attendance_date,
    shift_start,
    first_in,
    current_late_number
):
    try:
        sender_email = frappe.db.get_single_value("HR Settings", "sender_email") \
            or frappe.db.get_single_value("Email Account", "default_sender") or "no-reply@example.com"
        emp_first_name = (employee_name.split(" ")[0]).capitalize() if employee_name else "there"
        attendance_date_str = attendance_date
        shift_start_str = str(shift_start)[:5]
        first_in_str = str(first_in)[11:16]
        subject = f"Late Entry Notice - {attendance_date_str}"
        half_day_note = ""
        if current_late_number == 4:
            half_day_note = (
                "<p style='color:#b3261e;font-size:14px;font-weight:500;'>"
                "Please note: This is your 4th late entry for this month. "
                "As per policy, today has been marked for HR review."
                "</p>"
            )

        message = f"""
<body style="font-family: Arial, sans-serif; margin: 0; padding: 0">
  <div class="container" style="max-width: 600px; background-color: white; margin: 0 auto; border-radius: 10px;">
    <div class="container-body" style="padding: 32px 24px; background-color: #eaf1fe; border-radius: 12px;">
      <div class="header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
        <div class="logo">
          <img src="https://pw-images-dev.s3.ap-south-2.amazonaws.com/PWLogoForEmailV3.png" alt="PossibleWorks Logo" style="height:40px"/>
        </div>
      </div>
      <div class="content" style="color: #0f1e3d; border-radius: 12px">
        <h2 style="font-size: 20px; font-weight: 500; color: #0f1e3d;">
          Hey {emp_first_name},
        </h2>
        <p style="color: #3d475c; font-size: 14px; font-weight: 400;">
          This is to inform you that your check-in on <strong>{attendance_date_str}</strong>
          was recorded as a late entry.
        </p>
        <ul style="color: #3d475c; font-size: 14px; font-weight: 400; padding-left: 20px;">
          <li><strong>Shift Start Time:</strong> {shift_start_str}</li>
          <li><strong>Your First Check-in:</strong> {first_in_str}</li>
          <li><strong>Late Entry Count (This Month):</strong> {current_late_number}</li>
        </ul>
        {half_day_note}
        <p style="color: #3d475c; font-size: 14px; font-weight: 400;">
          If you believe this is an error, please reach out to your HR team.
        </p>
        <p style="color: #3d475c; font-size: 14px; font-weight: 400;">
          Best regards,<br>HR Team
        </p>
      </div>
    </div>
    <div class="footer" style="text-align: center; padding: 32px 20px; background-color: white; font-size: 12px; color: #2e5cb8; font-weight: 400;">
      <p>This email was sent from an unmonitored mailbox. You are receiving
        this email because you are part of the PossibleWorks organization.
        <a href="https://possibleworks.com/privacy-policy"
          style="color: #2e5cb8 !important; text-decoration: underline !important;">Privacy Statement</a>
      </p>
    </div>
  </div>
</body>
        """
        print("Sender Email:", sender_email)
        print("Employee Email:", employee_email)
        print("Email Body:\n", message)
        frappe.sendmail(
            sender=sender_email,
            recipients=[employee_email],
            subject=subject,
            message=message,
            header="Late Entry Notice",
        )
        print("Email successfully sent to", employee_email)
    except Exception as e:
        frappe.log_error(
            title=f"Email Send Error: {employee_id} ({employee_email})",
            message=str(e)
        )
        print(f"ERROR sending email for {employee_id} - {str(e)}")
        raise

execute()
