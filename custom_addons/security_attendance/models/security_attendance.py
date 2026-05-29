from datetime import datetime, time, timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SecurityAttendanceBatch(models.Model):
    _name = "security.attendance.batch"
    _description = "Security Posting Sheet Batch"
    _order = "attendance_date desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    attendance_date = fields.Date(required=True, default=fields.Date.context_today)
    partner_id = fields.Many2one("res.partner", string="Client")
    site_id = fields.Many2one("security.client.site", string="Client Site")
    roster_batch_id = fields.Many2one("security.roster.batch", string="Roster Batch")
    captured_by_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user.id,
        string="Captured By",
    )
    reviewed_by_id = fields.Many2one("res.users", string="Reviewed By")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("captured", "Captured"),
            ("reviewed", "Reviewed"),
            ("locked", "Locked"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
    )
    attendance_record_ids = fields.One2many(
        "security.attendance.record",
        "attendance_batch_id",
        string="Attendance Records",
    )
    record_count = fields.Integer(compute="_compute_record_count")
    absent_count = fields.Integer(compute="_compute_record_count")
    awol_count = fields.Integer(compute="_compute_record_count")
    note = fields.Text()

    @api.depends("attendance_date", "partner_id", "site_id")
    def _compute_name(self):
        for batch in self:
            scope = batch.site_id.name or batch.partner_id.name or "All Sites"
            batch.name = f"{batch.attendance_date} - {scope}" if batch.attendance_date else scope

    def _compute_record_count(self):
        for batch in self:
            records = batch.attendance_record_ids
            batch.record_count = len(records)
            batch.absent_count = len(records.filtered(lambda record: record.status == "absent"))
            batch.awol_count = len(records.filtered(lambda record: record.absence_type == "awol"))

    @api.onchange("site_id")
    def _onchange_site_id(self):
        for batch in self:
            if batch.site_id:
                batch.partner_id = batch.site_id.partner_id

    def action_generate_from_roster(self):
        record_model = self.env["security.attendance.record"]
        slot_model = self.env["security.roster.slot"]
        for batch in self:
            domain = [("shift_date", "=", batch.attendance_date), ("state", "!=", "cancelled")]
            if batch.roster_batch_id:
                domain.append(("batch_id", "=", batch.roster_batch_id.id))
            if batch.site_id:
                domain.append(("site_id", "=", batch.site_id.id))
            elif batch.partner_id:
                domain.append(("partner_id", "=", batch.partner_id.id))
            slots = slot_model.search(domain)
            if not slots:
                raise ValidationError("No roster slots found for this posting sheet batch.")
            created_count = 0
            for slot in slots:
                existing = record_model.search_count(
                    [
                        ("attendance_batch_id", "=", batch.id),
                        ("roster_slot_id", "=", slot.id),
                    ]
                )
                if existing:
                    continue
                record_model.create(
                    {
                        "attendance_batch_id": batch.id,
                        "roster_slot_id": slot.id,
                    }
                )
                created_count += 1
            batch.state = "captured"
            if not created_count:
                raise ValidationError("Attendance records already exist for the matching roster slots.")

    def action_review(self):
        for batch in self:
            batch.reviewed_by_id = self.env.user
            batch.state = "reviewed"

    def action_lock(self):
        for batch in self:
            batch.state = "locked"

    def action_cancel(self):
        for batch in self:
            batch.state = "cancelled"

    def action_reset_to_draft(self):
        for batch in self:
            batch.state = "draft"


class SecurityAttendanceRecord(models.Model):
    _name = "security.attendance.record"
    _description = "Security Attendance Record"
    _order = "shift_date desc, check_in desc, id desc"

    roster_slot_id = fields.Many2one(
        "security.roster.slot",
        required=True,
        ondelete="cascade",
    )
    attendance_batch_id = fields.Many2one(
        "security.attendance.batch",
        ondelete="set null",
        string="Posting Sheet Batch",
    )
    name = fields.Char(compute="_compute_name", store=True)
    shift_date = fields.Date(related="roster_slot_id.shift_date", store=True)
    employee_id = fields.Many2one(related="roster_slot_id.employee_id", store=True)
    partner_id = fields.Many2one(related="roster_slot_id.partner_id", store=True)
    site_id = fields.Many2one(related="roster_slot_id.site_id", store=True)
    post_id = fields.Many2one(related="roster_slot_id.post_id", store=True)
    shift_template_id = fields.Many2one(
        related="roster_slot_id.shift_template_id",
        store=True,
    )
    check_in = fields.Datetime()
    check_out = fields.Datetime()
    manual_presence = fields.Selection(
        [
            ("not_marked", "Not Marked"),
            ("present", "Present"),
            ("absent", "Absent"),
            ("awol", "AWOL"),
        ],
        default="not_marked",
        required=True,
        string="Posting Sheet Mark",
    )
    absence_type = fields.Selection(
        [
            ("none", "None"),
            ("authorised", "Authorised Absence"),
            ("awol", "AWOL"),
            ("no_show", "No Show"),
        ],
        default="none",
        required=True,
    )
    scheduled_start = fields.Datetime(
        compute="_compute_scheduled_datetimes",
        store=True,
    )
    scheduled_end = fields.Datetime(
        compute="_compute_scheduled_datetimes",
        store=True,
    )
    scheduled_hours = fields.Float(
        compute="_compute_attendance_metrics",
        store=True,
    )
    worked_hours = fields.Float(
        compute="_compute_attendance_metrics",
        store=True,
    )
    valid_hours = fields.Float(
        compute="_compute_attendance_metrics",
        store=True,
    )
    payable_hours = fields.Float(
        compute="_compute_attendance_metrics",
        store=True,
    )
    unpaid_hours = fields.Float(
        compute="_compute_attendance_metrics",
        store=True,
    )
    no_work_no_pay = fields.Boolean(
        compute="_compute_attendance_metrics",
        store=True,
    )
    overtime_hours = fields.Float(
        compute="_compute_attendance_metrics",
        store=True,
    )
    late_minutes = fields.Integer(
        compute="_compute_attendance_metrics",
        store=True,
    )
    early_departure_minutes = fields.Integer(
        compute="_compute_attendance_metrics",
        store=True,
    )
    missing_check_out = fields.Boolean(
        compute="_compute_attendance_metrics",
        store=True,
    )
    is_sunday = fields.Boolean(
        compute="_compute_calendar_flags",
        store=True,
    )
    is_public_holiday = fields.Boolean(
        compute="_compute_calendar_flags",
        store=True,
    )
    premium_category = fields.Selection(
        [
            ("normal", "Normal"),
            ("sunday", "Sunday"),
            ("public_holiday", "Public Holiday"),
        ],
        compute="_compute_calendar_flags",
        store=True,
    )
    overtime_approved = fields.Boolean(default=False)
    overtime_approved_by_id = fields.Many2one("res.users", string="Overtime Approved By")
    overtime_approval_note = fields.Char()
    status = fields.Selection(
        [
            ("scheduled", "Scheduled"),
            ("present", "Present"),
            ("late", "Late"),
            ("early_leave", "Early Leave"),
            ("absent", "Absent"),
            ("incomplete", "Incomplete"),
        ],
        compute="_compute_attendance_metrics",
        store=True,
    )
    override_reason = fields.Char()
    note = fields.Text()

    @api.depends(
        "roster_slot_id.shift_date",
        "roster_slot_id.shift_template_id.start_hour",
        "roster_slot_id.shift_template_id.end_hour",
    )
    def _compute_scheduled_datetimes(self):
        for record in self:
            record.scheduled_start = False
            record.scheduled_end = False
            shift_date = record.roster_slot_id.shift_date
            template = record.roster_slot_id.shift_template_id
            if not shift_date or not template:
                continue

            start_hour = int(template.start_hour)
            start_minute = int(round((template.start_hour - start_hour) * 60))
            end_hour = int(template.end_hour)
            end_minute = int(round((template.end_hour - end_hour) * 60))

            start_dt = datetime.combine(
                shift_date,
                time(hour=start_hour, minute=start_minute),
            )
            end_dt = datetime.combine(
                shift_date,
                time(hour=end_hour, minute=end_minute),
            )
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)

            record.scheduled_start = fields.Datetime.to_string(start_dt)
            record.scheduled_end = fields.Datetime.to_string(end_dt)

    @api.depends(
        "scheduled_start",
        "scheduled_end",
        "check_in",
        "check_out",
        "manual_presence",
        "absence_type",
        "overtime_approved",
    )
    def _compute_attendance_metrics(self):
        for record in self:
            record.scheduled_hours = 0.0
            record.worked_hours = 0.0
            record.valid_hours = 0.0
            record.payable_hours = 0.0
            record.unpaid_hours = 0.0
            record.no_work_no_pay = False
            record.overtime_hours = 0.0
            record.late_minutes = 0
            record.early_departure_minutes = 0
            record.missing_check_out = False
            record.status = "scheduled"

            if record.scheduled_start and record.scheduled_end:
                start = fields.Datetime.to_datetime(record.scheduled_start)
                end = fields.Datetime.to_datetime(record.scheduled_end)
                record.scheduled_hours = max((end - start).total_seconds() / 3600.0, 0.0)
            else:
                continue

            if record.manual_presence in ("absent", "awol"):
                record.status = "absent"
                record.no_work_no_pay = True
                record.unpaid_hours = record.scheduled_hours
                continue

            if not record.check_in and not record.check_out:
                record.status = "absent"
                record.no_work_no_pay = True
                record.unpaid_hours = record.scheduled_hours
                continue

            if record.check_in and not record.check_out:
                record.missing_check_out = True
                record.status = "incomplete"
                continue

            if record.check_in and record.check_out:
                check_in = fields.Datetime.to_datetime(record.check_in)
                check_out = fields.Datetime.to_datetime(record.check_out)
                if check_out > check_in:
                    record.worked_hours = (check_out - check_in).total_seconds() / 3600.0
                    overlap_start = max(start, check_in)
                    overlap_end = min(end, check_out)
                    if overlap_end > overlap_start:
                        record.valid_hours = (
                            overlap_end - overlap_start
                        ).total_seconds() / 3600.0
                    extra_seconds = max((check_out - end).total_seconds(), 0.0)
                    record.overtime_hours = extra_seconds / 3600.0 if record.overtime_approved else 0.0
                    record.payable_hours = record.valid_hours + record.overtime_hours
                    record.unpaid_hours = max(record.scheduled_hours - record.valid_hours, 0.0)
                    record.no_work_no_pay = bool(record.unpaid_hours)

                if check_in > start:
                    record.late_minutes = int((check_in - start).total_seconds() // 60)
                if check_out < end:
                    record.early_departure_minutes = int(
                        (end - check_out).total_seconds() // 60
                    )

                if record.late_minutes:
                    record.status = "late"
                elif record.early_departure_minutes:
                    record.status = "early_leave"
                else:
                    record.status = "present"

    @api.depends("shift_date")
    def _compute_calendar_flags(self):
        for record in self:
            record.is_sunday = bool(record.shift_date and record.shift_date.weekday() == 6)
            holiday = False
            if record.shift_date and "security.public.holiday" in self.env:
                holiday = self.env["security.public.holiday"].search_count(
                    [
                        ("holiday_date", "=", record.shift_date),
                        ("active", "=", True),
                    ]
                )
            record.is_public_holiday = bool(holiday)
            if record.is_public_holiday:
                record.premium_category = "public_holiday"
            elif record.is_sunday:
                record.premium_category = "sunday"
            else:
                record.premium_category = "normal"

    @api.onchange("manual_presence")
    def _onchange_manual_presence(self):
        for record in self:
            if record.manual_presence == "awol":
                record.absence_type = "awol"
            elif record.manual_presence == "absent" and record.absence_type == "none":
                record.absence_type = "no_show"
            elif record.manual_presence == "present":
                record.absence_type = "none"

    def action_mark_awol(self):
        for record in self:
            record.manual_presence = "awol"
            record.absence_type = "awol"

    def action_approve_overtime(self):
        for record in self:
            record.overtime_approved = True
            record.overtime_approved_by_id = self.env.user

    @api.depends("roster_slot_id", "employee_id", "shift_date")
    def _compute_name(self):
        for record in self:
            employee = record.employee_id.name or "Unassigned"
            date = record.shift_date or ""
            record.name = f"{employee} - {date}"
