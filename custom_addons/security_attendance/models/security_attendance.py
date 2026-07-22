from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.security_attendance.utils.shift_split import split_shift_by_boundaries


class SecurityAttendanceBatch(models.Model):
    _name = "security.attendance.batch"
    _description = "Security Posting Sheet Batch"
    _order = "attendance_date desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    attendance_date = fields.Date(required=True, default=fields.Date.context_today)
    partner_id = fields.Many2one("res.partner", string="Client", domain=[("is_company", "=", True)])
    site_id = fields.Many2one("security.client.site", string="Client Site", domain="[('partner_id','=',partner_id)]")
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
    missing_checkin_count = fields.Integer(compute="_compute_record_count", string="Missing Check-ins")
    note = fields.Text()

    @api.depends("attendance_date", "partner_id", "site_id")
    def _compute_name(self):
        for batch in self:
            scope = batch.site_id.name or batch.partner_id.name or "All Sites"
            batch.name = f"{batch.attendance_date} - {scope}" if batch.attendance_date else scope

    def _compute_record_count(self):
        from datetime import datetime, timedelta
        now_utc = datetime.utcnow()
        cutoff = now_utc - timedelta(minutes=15)
        for batch in self:
            records = batch.attendance_record_ids
            batch.record_count = len(records)
            batch.absent_count = len(records.filtered(lambda record: record.status == "absent"))
            batch.awol_count = len(records.filtered(lambda record: record.absence_type == "awol"))
            missing = 0
            for rec in records:
                if rec.manual_presence in ("absent", "awol"):
                    continue
                if rec.check_in:
                    continue
                sched = fields.Datetime.to_datetime(rec.scheduled_start)
                if sched and sched <= cutoff:
                    missing += 1
            batch.missing_checkin_count = missing

    @api.onchange("site_id")
    def _onchange_site_id(self):
        for batch in self:
            if batch.site_id:
                batch.partner_id = batch.site_id.partner_id

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        for batch in self:
            if batch.site_id and batch.site_id.partner_id != batch.partner_id:
                batch.site_id = False

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
            all_slots = slot_model.search(domain)
            if not all_slots:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "No Roster Slots Found",
                        "message": (
                            f"No roster slots exist for {batch.attendance_date} "
                            f"at {batch.site_id.name or 'this site'}. "
                            "Create roster slots with assigned guards first, "
                            "then generate the attendance sheet."
                        ),
                        "type": "warning",
                        "sticky": True,
                    },
                }
            slots = all_slots.filtered(lambda s: s.employee_id)
            unassigned_count = len(all_slots) - len(slots)
            if not slots:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Guards Not Assigned",
                        "message": (
                            f"Found {len(all_slots)} roster slot(s) for "
                            f"{batch.site_id.name or 'this site'} on {batch.attendance_date}, "
                            "but none have guards assigned. "
                            "Assign guards in the Roster Board first."
                        ),
                        "type": "warning",
                        "sticky": True,
                    },
                }
            created_count = 0
            skipped_count = 0
            for slot in slots:
                existing = record_model.search_count(
                    [
                        ("attendance_batch_id", "=", batch.id),
                        ("roster_slot_id", "=", slot.id),
                    ]
                )
                if existing:
                    skipped_count += 1
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
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Already Generated",
                        "message": (
                            f"All {skipped_count} assigned slot(s) already have attendance records. "
                            "No new records were created."
                        ),
                        "type": "info",
                        "sticky": False,
                    },
                }
            msg = f"{created_count} attendance record(s) generated from roster."
            if unassigned_count:
                msg += f" Note: {unassigned_count} unassigned slot(s) were skipped."
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Roster Generated",
                    "message": msg,
                    "type": "success",
                    "sticky": False,
                },
            }

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

    def action_bulk_mark_attendance(self, records_data):
        """
        Bulk update attendance records from the Posting Console OWL client action.
        records_data: list of {record_id, manual_presence, check_in, check_out}
        """
        self.ensure_one()
        record_model = self.env["security.attendance.record"]
        for item in records_data:
            record = record_model.browse(item.get("record_id"))
            if not record.exists():
                continue
            vals = {"manual_presence": item.get("manual_presence", "not_marked")}
            if item.get("check_in"):
                vals["check_in"] = item["check_in"]
            if item.get("check_out"):
                vals["check_out"] = item["check_out"]
            record.write(vals)
        if self.state == "draft":
            self.state = "captured"

    def action_open_posting_console(self):
        return {
            "type": "ir.actions.client",
            "tag": "security_attendance.posting_console",
            "target": "current",
            "context": {
                "default_batch_id": self.id,
                "default_date": str(self.attendance_date) if self.attendance_date else False,
                "default_site_id": self.site_id.id if self.site_id else False,
            },
        }


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
    hr_attendance_id = fields.Many2one(
        "hr.attendance",
        string="Linked HR Attendance",
        ondelete="set null",
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
    is_saturday = fields.Boolean(
        compute="_compute_calendar_flags",
        store=True,
    )
    is_public_holiday = fields.Boolean(
        compute="_compute_calendar_flags",
        store=True,
    )
    is_night_shift = fields.Boolean(
        compute="_compute_shift_buckets",
        store=True,
    )
    premium_category = fields.Selection(
        [
            ("normal", "Normal"),
            ("saturday", "Saturday"),
            ("sunday", "Sunday"),
            ("public_holiday", "Public Holiday"),
        ],
        compute="_compute_calendar_flags",
        store=True,
    )
    # Hour buckets — split by pay category using split_shift_by_boundaries().
    # Payroll reads these fields; the old premium_category + payable_hours
    # approach only handled three categories and ignored night/saturday.
    normal_hours = fields.Float(compute="_compute_shift_buckets", store=True)
    sunday_hours = fields.Float(compute="_compute_shift_buckets", store=True)
    public_holiday_hours = fields.Float(compute="_compute_shift_buckets", store=True)
    saturday_hours = fields.Float(compute="_compute_shift_buckets", store=True)
    night_hours = fields.Float(compute="_compute_shift_buckets", store=True)
    overtime_approved = fields.Boolean(default=False)
    overtime_approved_by_id = fields.Many2one("res.users", string="Overtime Approved By")
    overtime_approval_note = fields.Char()
    billing_contract_id = fields.Many2one(
        "security.client.contract",
        compute="_compute_billing_amount",
        string="Billing Contract",
        store=False,
    )
    billing_amount = fields.Float(
        compute="_compute_billing_amount",
        string="Billing Amount",
        digits=(10, 2),
        store=False,
    )
    billing_approved = fields.Boolean(default=False, string="Billing Approved")
    billing_approved_by_id = fields.Many2one("res.users", string="Approved By", readonly=True)
    billing_approved_date = fields.Datetime(string="Approval Date", readonly=True)
    has_billing_exception = fields.Boolean(
        compute="_compute_has_billing_exception",
        store=True,
        string="Has Billing Exception",
    )
    billing_exception_reason = fields.Char(
        compute="_compute_billing_exception_reason",
        string="Exception Reason",
    )
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

            tz_name = self.env.user.tz or self.env.company.partner_id.tz or "UTC"
            tz = pytz.timezone(tz_name)

            start_dt_local = datetime.combine(
                shift_date,
                time(hour=start_hour, minute=start_minute),
            )
            end_dt_local = datetime.combine(
                shift_date,
                time(hour=end_hour, minute=end_minute),
            )
            if end_dt_local <= start_dt_local:
                end_dt_local += timedelta(days=1)

            start_dt_utc = tz.localize(start_dt_local).astimezone(pytz.utc).replace(tzinfo=None)
            end_dt_utc = tz.localize(end_dt_local).astimezone(pytz.utc).replace(tzinfo=None)

            record.scheduled_start = fields.Datetime.to_string(start_dt_utc)
            record.scheduled_end = fields.Datetime.to_string(end_dt_utc)

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
            weekday = record.shift_date.weekday() if record.shift_date else -1
            record.is_sunday = weekday == 6
            record.is_saturday = weekday == 5
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
            elif record.is_saturday:
                record.premium_category = "saturday"
            else:
                record.premium_category = "normal"

    @api.depends(
        "scheduled_start",
        "scheduled_end",
        "check_in",
        "check_out",
        "manual_presence",
        "absence_type",
        "shift_date",
    )
    def _compute_shift_buckets(self):
        """
        Split payable hours into pay-category buckets using split_shift_by_boundaries.
        Only runs when an actual payable window can be determined.
        """
        for record in self:
            record.normal_hours = 0.0
            record.sunday_hours = 0.0
            record.public_holiday_hours = 0.0
            record.saturday_hours = 0.0
            record.night_hours = 0.0
            record.is_night_shift = False

            if record.manual_presence in ("absent", "awol"):
                continue
            if record.absence_type in ("awol", "no_show"):
                continue

            scheduled_start = fields.Datetime.to_datetime(record.scheduled_start)
            scheduled_end = fields.Datetime.to_datetime(record.scheduled_end)
            if not scheduled_start or not scheduled_end:
                continue

            # Determine the payable time window.
            if record.check_in and record.check_out:
                check_in = fields.Datetime.to_datetime(record.check_in)
                check_out = fields.Datetime.to_datetime(record.check_out)
                if check_out <= check_in:
                    continue
                pay_start = max(scheduled_start, check_in)
                pay_end = min(scheduled_end, check_out)
                if pay_end <= pay_start:
                    continue
            elif record.manual_presence == "present":
                pay_start = scheduled_start
                pay_end = scheduled_end
            else:
                continue

            # Fetch public holidays once per record.
            public_holidays = []
            if "security.public.holiday" in self.env:
                from datetime import date as date_type
                start_date = pay_start.date()
                end_date = pay_end.date()
                holidays = self.env["security.public.holiday"].search(
                    [
                        ("holiday_date", ">=", start_date),
                        ("holiday_date", "<=", end_date),
                        ("active", "=", True),
                    ]
                )
                public_holidays = [h.holiday_date for h in holidays]

            buckets = split_shift_by_boundaries(pay_start, pay_end, public_holidays)
            record.normal_hours = buckets["normal_hours"]
            record.sunday_hours = buckets["sunday_hours"]
            record.public_holiday_hours = buckets["public_holiday_hours"]
            record.saturday_hours = buckets["saturday_hours"]
            record.night_hours = buckets["night_hours"]
            record.is_night_shift = buckets["night_hours"] > 0

    @api.depends(
        "normal_hours", "night_hours", "saturday_hours", "sunday_hours",
        "public_holiday_hours", "overtime_hours", "overtime_approved",
        "site_id", "shift_date", "employee_id",
    )
    def _compute_billing_amount(self):
        contract_model = self.env.get("security.client.contract")
        for record in self:
            record.billing_contract_id = False
            record.billing_amount = 0.0
            if not contract_model or not record.site_id or not record.shift_date:
                continue
            contract = contract_model.get_active_for_site(record.site_id, record.shift_date)
            if not contract:
                continue
            record.billing_contract_id = contract.id
            grade = record.employee_id.security_grade_id if record.employee_id else None
            amount = 0.0
            buckets = {
                "normal": record.normal_hours or 0.0,
                "night": record.night_hours or 0.0,
                "saturday": record.saturday_hours or 0.0,
                "sunday": record.sunday_hours or 0.0,
                "public_holiday": record.public_holiday_hours or 0.0,
            }
            for category, hours in buckets.items():
                if hours > 0:
                    rate = contract.get_rate_for(grade, category)
                    amount += hours * rate
            if record.overtime_approved and record.overtime_hours:
                ot_rate = contract.get_rate_for(grade, "normal")
                amount += record.overtime_hours * ot_rate
            record.billing_amount = round(amount, 2)

    @api.depends(
        "status", "late_minutes", "early_departure_minutes",
        "missing_check_out", "absence_type", "manual_presence",
        "overtime_hours", "overtime_approved",
    )
    def _compute_has_billing_exception(self):
        for record in self:
            has_exc = False
            if record.manual_presence == "awol" or record.absence_type == "awol":
                has_exc = True
            elif record.status == "absent" and record.absence_type not in ("authorised",):
                has_exc = True
            elif record.late_minutes > 0:
                has_exc = True
            elif record.early_departure_minutes > 0:
                has_exc = True
            elif record.missing_check_out:
                has_exc = True
            elif record.overtime_hours > 0 and not record.overtime_approved:
                has_exc = True
            record.has_billing_exception = has_exc

    @api.depends(
        "status", "late_minutes", "early_departure_minutes",
        "missing_check_out", "absence_type", "manual_presence",
        "overtime_hours", "overtime_approved",
    )
    def _compute_billing_exception_reason(self):
        for record in self:
            reasons = []
            if record.manual_presence == "awol" or record.absence_type == "awol":
                reasons.append("AWOL")
            elif record.status == "absent":
                reasons.append("Absent")
            if record.late_minutes > 0:
                reasons.append(f"Late {record.late_minutes}min")
            if record.early_departure_minutes > 0:
                reasons.append(f"Early leave {record.early_departure_minutes}min")
            if record.missing_check_out:
                reasons.append("Missing check-out")
            if record.overtime_hours > 0 and not record.overtime_approved:
                reasons.append("Unapproved OT")
            record.billing_exception_reason = "; ".join(reasons) if reasons else ""

    def action_approve_billing(self):
        for record in self:
            record.billing_approved = True
            record.billing_approved_by_id = self.env.user
            record.billing_approved_date = fields.Datetime.now()

    def action_reset_billing_approval(self):
        for record in self:
            record.billing_approved = False
            record.billing_approved_by_id = False
            record.billing_approved_date = False

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

    @api.model
    def _group_expand_status(self, statuses, domain, order):
        return [key for key, _ in type(self).status.selection]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_hr_attendance()
        # DeployGuard Intelligence Bus Event
        event_model = self.env.get("security.event.log")
        if event_model:
            for rec in records:
                if rec.manual_presence in ["absent", "awol"] or rec.absence_type == "awol":
                    event_model.register_event("attendance.missed", "security.attendance.record", rec.id)
        return records

    def write(self, vals):
        awol_triggered = (
            vals.get("manual_presence") == "awol"
            or vals.get("absence_type") == "awol"
        )
        result = super().write(vals)
        if awol_triggered:
            self.sudo()._notify_awol()
        
        # DeployGuard Intelligence Bus Event
        event_model = self.env.get("security.event.log")
        if event_model and (vals.get("manual_presence") in ["absent", "awol"] or vals.get("absence_type") == "awol"):
            for rec in self:
                event_model.register_event("attendance.missed", "security.attendance.record", rec.id)
        
        fields_to_sync = {"manual_presence", "check_in", "check_out", "employee_id"}
        if any(f in vals for f in fields_to_sync):
            self._sync_hr_attendance()
            
        return result

    def unlink(self):
        linked_attendances = self.mapped("hr_attendance_id")
        result = super().unlink()
        if linked_attendances:
            linked_attendances.sudo().unlink()
        return result

    def _sync_hr_attendance(self):
        if "hr.attendance" not in self.env:
            return
        for record in self:
            rec_sudo = record.sudo()
            employee = rec_sudo.employee_id
            check_in = rec_sudo.check_in
            check_out = rec_sudo.check_out
            is_present = rec_sudo.manual_presence == "present"

            if is_present and employee and check_in:
                vals = {
                    "employee_id": employee.id,
                    "check_in": check_in,
                    "check_out": check_out or False,
                }
                if rec_sudo.hr_attendance_id:
                    rec_sudo.hr_attendance_id.write(vals)
                else:
                    new_attendance = self.env["hr.attendance"].sudo().create(vals)
                    super(SecurityAttendanceRecord, record).write({"hr_attendance_id": new_attendance.id})
            else:
                if rec_sudo.hr_attendance_id:
                    linked_att = rec_sudo.hr_attendance_id
                    super(SecurityAttendanceRecord, record).write({"hr_attendance_id": False})
                    linked_att.unlink()

    def _notify_awol(self):
        notification_model = self.env.get("security.notification")
        if not notification_model:
            return
        for rec in self:
            if rec.manual_presence != "awol" and rec.absence_type != "awol":
                continue
            recipients = self.env["res.users"].browse()
            site = rec.site_id
            if site and site.supervisor_id and site.supervisor_id.user_id:
                recipients |= site.supervisor_id.user_id
            mgr_users = self.env["res.users"].search(
                [("group_ids", "in", [self.env.ref("base.group_system").id])],
                limit=3,
            )
            recipients |= mgr_users

            replacement_hint = ""
            slot = rec.roster_slot_id
            if slot and hasattr(slot, "_get_eligible_guards"):
                try:
                    eligible = slot._get_eligible_guards(slot)
                    if eligible:
                        if hasattr(slot, "_score_guard"):
                            scored = sorted(
                                [(slot._score_guard(slot, e)[0], e) for e, _ in eligible[:5]],
                                key=lambda x: x[0],
                                reverse=True,
                            )
                            best_emp = scored[0][1]
                        else:
                            best_emp = eligible[0][0]
                        replacement_hint = f" Suggested replacement: {best_emp.name}."
                except Exception:
                    pass

            notification_model.create({
                "title": f"AWOL: {rec.employee_id.name or 'Unknown Guard'}",
                "body": (
                    f"{rec.employee_id.name or 'Guard'} marked AWOL at "
                    f"{rec.site_id.name or 'unknown site'} on {rec.shift_date}."
                    f"{replacement_hint}"
                ),
                "notification_type": "awol_alert",
                "severity": "critical",
                "recipient_ids": [(6, 0, recipients.ids)],
                "related_model": "security.attendance.record",
                "related_id": rec.id,
            })

    @api.depends("roster_slot_id", "employee_id", "shift_date")
    def _compute_name(self):
        for record in self:
            employee = record.employee_id.name or "Unassigned"
            date = record.shift_date or ""
            record.name = f"{employee} - {date}"


# ─────────────────────────────────────────────────────────────────────────────
# ATTENDANCE SUMMARY GRID DATA PROVIDER
# ─────────────────────────────────────────────────────────────────────────────

class SecurityAttendanceGrid(models.AbstractModel):
    _name = "security.attendance.grid"
    _description = "Attendance Summary Grid Data Provider"

    @api.model
    def get_grid_data(self, month_str=None, site_id=None):
        from datetime import date as _date, timedelta
        import calendar

        today = _date.today()
        if month_str:
            year, month = int(month_str[:4]), int(month_str[5:7])
        else:
            year, month = today.year, today.month

        month_start = _date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        month_end = _date(year, month, last_day)

        domain = [
            ("shift_date", ">=", str(month_start)),
            ("shift_date", "<=", str(month_end)),
        ]
        if site_id:
            domain.append(("site_id", "=", site_id))

        Record = self.env["security.attendance.record"]
        records = Record.search(domain)

        # Group by date
        from collections import defaultdict
        by_date = defaultdict(lambda: {"scheduled": 0, "present": 0, "absent": 0, "awol": 0, "late": 0, "not_marked": 0})
        for r in records:
            key = str(r.shift_date)
            by_date[key]["scheduled"] += 1
            mp = r.manual_presence or "not_marked"
            if mp in by_date[key]:
                by_date[key][mp] += 1
            else:
                by_date[key]["not_marked"] += 1

        # Build day list
        days = []
        cur = month_start
        while cur <= month_end:
            key = str(cur)
            stats = by_date[key]
            pct = round(100 * stats["present"] / stats["scheduled"]) if stats["scheduled"] else None
            days.append({
                "date": key,
                "day": cur.day,
                "weekday": cur.strftime("%a"),
                "weekday_num": cur.weekday(),
                "scheduled": stats["scheduled"],
                "present": stats["present"],
                "absent": stats["absent"],
                "awol": stats["awol"],
                "late": stats["late"],
                "not_marked": stats["not_marked"],
                "pct": pct,
            })
            cur += timedelta(days=1)

        # Totals
        totals = {"scheduled": 0, "present": 0, "absent": 0, "awol": 0, "late": 0}
        for d in days:
            for k in totals:
                totals[k] += d[k]

        # Site filter options
        Site = self.env["security.client.site"]
        sites = Site.search([("active", "=", True)], order="name asc")

        # By-site summary for the month
        by_site = {}
        for r in records:
            sid = r.site_id.id if r.site_id else 0
            sname = r.site_id.name if r.site_id else "No Site"
            if sid not in by_site:
                by_site[sid] = {"id": sid, "name": sname, "scheduled": 0, "present": 0, "absent": 0, "awol": 0}
            by_site[sid]["scheduled"] += 1
            if r.manual_presence == "present":
                by_site[sid]["present"] += 1
            elif r.manual_presence == "absent":
                by_site[sid]["absent"] += 1
            elif r.manual_presence == "awol":
                by_site[sid]["awol"] += 1

        site_summary = sorted(by_site.values(), key=lambda x: -x["scheduled"])
        for s in site_summary:
            s["pct"] = round(100 * s["present"] / s["scheduled"]) if s["scheduled"] else None

        return {
            "month_label": month_start.strftime("%B %Y"),
            "month_str": month_start.strftime("%Y-%m"),
            "days": days,
            "totals": totals,
            "sites": [{"id": s.id, "name": s.name} for s in sites],
            "site_summary": site_summary,
        }
