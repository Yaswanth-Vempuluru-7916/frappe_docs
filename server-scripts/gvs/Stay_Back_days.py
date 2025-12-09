def execute():
    print("=" * 70)
    print("STARTING STAYBACK ABSENT CHECK (Prioritize Present/Working, fallback to Half Day)")
    print("=" * 70)

    today = frappe.utils.getdate('2025-12-08')
    weekday = today.weekday()
    if weekday == 6:  # Today is Sunday
        days_since_sunday = 7
    else:
        days_since_sunday = weekday + 1

    end_of_week = frappe.utils.add_days(today, -days_since_sunday)  # Last Sunday
    start_of_week = frappe.utils.add_days(end_of_week, -6)  # Previous Monday

    print(f"Checking previous week: {str(start_of_week)} to {str(end_of_week)}")

    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active", "default_shift": "Vacation Staff Shift"},
        fields=["name", "employee_name", "default_shift", "company_email", "user_id"]
    )
    print(f"Found {len(employees)} vacation staff employees")

    for emp in employees:
        print("-" * 60)
        print(f"Processing: {emp.get('employee_name')} ({emp.get('name')})")
        
        # 1. Check for any Present/Working days
        pres_att = frappe.get_all(
            "Attendance",
            filters={
                "employee": emp.name,
                "attendance_date": ["between", [str(start_of_week), str(end_of_week)]],
                "docstatus": 1,
                "status": ["in", ["Present", "Working"]]
            },
            fields=["name", "attendance_date", "working_hours", "status"],
            order_by="attendance_date asc"
        )
        
        found_8_25 = False
        below_pres = []
        for att in pres_att:
            wh = 0
            try:
                wh = float(att.get("working_hours") or 0)
            except Exception:
                pass
            print(f"{att['attendance_date']}[{att['status']}]: {wh}")
            if wh >= 8.25:
                found_8_25 = True
            else:
                below_pres.append([str(att["attendance_date"]), att["name"], wh, att['status']])

        # If there's a present/working stay back, do nothing
        if found_8_25:
            print("Attendance OK: at least one 'Present'/'Working' day >= 8.25 hours.")
            continue

        # If any Present/Working < 8.25, mark the first as absent
        if below_pres:
            first = sorted(below_pres, key=lambda t: t[0])[0]
            mark_absent_and_notify(emp, first[0], first[1], first[2], first[3])
            continue

        # 2. Otherwise, try Half Day records
        half_att = frappe.get_all(
            "Attendance",
            filters={
                "employee": emp.name,
                "attendance_date": ["between", [str(start_of_week), str(end_of_week)]],
                "docstatus": 1,
                "status": "Half Day"
            },
            fields=["name", "attendance_date", "working_hours", "status"],
            order_by="attendance_date asc"
        )
        below_half = []
        for att in half_att:
            wh = 0
            try:
                wh = float(att.get("working_hours") or 0)
            except Exception:
                pass
            print(f"{att['attendance_date']}[Half Day]: {wh}")
            below_half.append([str(att["attendance_date"]), att["name"], wh, att['status']])
        if below_half:
            first = sorted(below_half, key=lambda t: t[0])[0]
            mark_absent_and_notify(emp, first[0], first[1], first[2], first[3])
        else:
            print("Attendance OK: No Present/Working/Half Day in week or all are sufficient.")

    print("=" * 70)
    print("END OF STAYBACK ABSENT CHECK")
    print("=" * 70)

def mark_absent_and_notify(emp, absent_day, att_name, worked, old_status):
    try:
        if att_name:
            att = frappe.get_doc("Attendance", att_name)
            print(f"Found existing attendance record: {att_name} (status was {old_status})")
            if att.docstatus == 1:
                att.cancel()
            att.delete()
            print(f"Deleted old attendance record: {att_name}")
        att = frappe.new_doc("Attendance")
        att.employee = emp.name
        att.employee_name = emp.employee_name
        att.attendance_date = absent_day
        att.company = frappe.db.get_value("Employee", emp.name, "company")
        att.shift = emp.default_shift
        att.status = "Absent"
        att.flags.ignore_permissions = True
        att.save()
        att.submit()
        comment_text = (
            f"Marked Absent on {absent_day} as this was not an attended stay back day (no day >= 8h 15m, original status: {old_status}). "
            f"Actual worked: {worked:.2f} hours."
        )
        att.add_comment("Comment", comment_text)
        frappe.get_doc("Employee", emp.name).add_comment("Comment", comment_text)
        print("Attendance marked Absent and comment added for", emp.employee_name)
        send_stayback_absent_mail(emp, absent_day, worked)
    except Exception as e:
        frappe.log_error(
            title=f"Stayback Absent Marking Error: {emp.name} ({absent_day})",
            message=str(e)
        )
        print(f"ERROR marking absence for {emp.name} - {str(e)}")

def send_stayback_absent_mail(emp, absent_day, worked):
    try:
        sender_email = frappe.db.get_single_value("HR Settings", "sender_email")
        if not sender_email:
            sender_email = frappe.db.get_single_value("Email Account", "default_sender") or "no-reply@example.com"
        employee_email = emp.user_id or emp.company_email
        emp_first = emp.employee_name.split(" ")[0].capitalize() if emp.employee_name else "there"
        attendance_date_str = str(absent_day)
        subject = f"Stay Back Day Policy Violation - {attendance_date_str}"
        worked_h = int(worked)
        worked_m = int(round((worked - worked_h) * 60))
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
          Dear {emp_first},
        </h2>
        <p style="color: #3d475c; font-size: 14px; font-weight: 400;">
            As per the Stay Back policy, it is required to complete a minimum of 8 hours of work on at least one day during the week.
        </p>
        <ul style="color: #3d475c; font-size: 14px; font-weight: 400; padding-left: 20px;">
          <li><strong>Date marked as Absent</strong> {attendance_date_str}</li>
          <li><strong>Recorded working hours on that day:</strong> {worked_h}h {worked_m}m</li>
        </ul>
        <p style='color:#b3261e;font-size:14px;font-weight:500;'>
          Since there was no day during the week where the required stay-back duration (≥ 8 hours) was completed, the above-mentioned date has been marked as Absent (LOP) in your attendance records.
        </p>
        <p style="color: #3d475c; font-size: 14px; font-weight: 400;">
          If you believe this marking is incorrect or need any clarification, please feel free to reach out to the HR team.
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
            header="Stayback Attendance Notice",
        )
        print("Email successfully sent to", employee_email)
    except Exception as e:
        frappe.log_error(
            title=f"Stayback Absent Email Error: {emp.name} ({absent_day})",
            message=str(e)
        )
        print(f"ERROR sending stayback absent email for {emp.name} - {str(e)}")

execute()
