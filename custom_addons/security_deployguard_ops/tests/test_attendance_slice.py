from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAttendanceSlice(TransactionCase):
    """The first V2 vertical slice, end to end:
    roster -> tasks -> guided task -> real posting sheet -> tasks complete
    from the records -> the GM sees it; overdue work becomes an exception."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ref = cls.env.ref
        base = ref("base.group_user")
        hr_user = ref("hr.group_hr_user")

        def user(login, *groups):
            return cls.env["res.users"].create({
                "name": login.split("@")[0], "login": login, "tz": "Africa/Lusaka",
                "group_ids": [(6, 0, [base.id, hr_user.id] + [g.id for g in groups])],
            })

        cls.ops_user = user("ops@slice.test", ref("security_base.group_security_supervisor"))
        cls.admin_user = user("admin@slice.test", ref("security_operations.group_security_front_desk"))
        cls.hr_user = user("hr@slice.test", ref("security_base.group_security_hr_payroll_officer"))
        cls.gm_user = user("gm@slice.test", ref("security_base.group_security_manager"))
        emp = cls.env["hr.employee"]
        cls.ops = emp.create({"name": "Ops Supervisor", "user_id": cls.ops_user.id, "tz": "Africa/Lusaka"})
        cls.admin = emp.create({"name": "Admin", "user_id": cls.admin_user.id, "tz": "Africa/Lusaka"})
        cls.hr = emp.create({"name": "HR", "user_id": cls.hr_user.id, "tz": "Africa/Lusaka"})
        cls.guards = emp.create([{"name": f"Guard {i}", "security_guard": True} for i in range(3)])

        partner = cls.env["res.partner"].create({"name": "ABC Mall", "is_company": True})
        cls.site = cls.env["security.client.site"].create({"name": "ABC Mall", "partner_id": partner.id})
        post_type = cls.env["security.post.type"].create({"name": "Standard"})
        post = cls.env["security.post"].create({"name": "Main Gate", "site_id": cls.site.id, "post_type_id": post_type.id})
        shift = cls.env["security.shift.template"].create({"name": "Day", "start_hour": 6.0, "end_hour": 18.0})
        cls.today = fields.Date.context_today(cls.env["security.work.task"].with_user(cls.ops_user))
        for guard in cls.guards:
            cls.env["security.roster.slot"].create({
                "shift_date": cls.today, "post_id": post.id, "shift_template_id": shift.id,
                "employee_id": guard.id, "state": "confirmed",
            })

        wizard = cls.env["security.deployguard.pipeline.setup"].with_user(cls.gm_user).create({
            "register_employee_id": cls.ops.id, "confirm_employee_id": cls.admin.id, "verify_employee_id": cls.hr.id,
        })
        wizard.action_apply()
        Task = cls.env["security.work.task"]
        cls.register = Task.search([("employee_id", "=", cls.ops.id), ("roster_date", "=", cls.today)])
        cls.confirm = Task.search([("employee_id", "=", cls.admin.id), ("roster_date", "=", cls.today)])
        cls.verify = Task.search([("employee_id", "=", cls.hr.id), ("roster_date", "=", cls.today)])

    def _batch(self):
        return self.env["security.attendance.batch"].search([("site_id", "=", self.site.id), ("attendance_date", "=", self.today)])

    def test_roster_creates_one_task_per_step_for_the_rostered_site(self):
        self.assertEqual((len(self.register), len(self.confirm), len(self.verify)), (1, 1, 1))
        card = self.env["security.work.task"].with_user(self.ops_user).get_my_today()["tasks"][0]
        self.assertEqual(card["guidance_flow_code"], "attendance_register")
        self.assertEqual(card["training"]["course_name"], "Daily Attendance: Register, Confirm, Verify")
        self.assertFalse(card["training"]["done"])
        self.assertTrue(card["why_it_matters"])
        admin_card = self.env["security.work.task"].with_user(self.admin_user).get_my_today()["tasks"][0]
        self.assertEqual(admin_card["readiness"], "waiting")

    def test_guided_register_is_verified_against_the_posting_sheet(self):
        Session = self.env["security.guidance.session"].with_user(self.ops_user)
        payload = Session.start("attendance_register")
        self.assertEqual(payload["task"]["id"], self.register.id, "uses the employee's real task, not practice")
        self.assertEqual(payload["step"]["title"], "Open the Posting Console")

        payload = Session.report_ui_state({"client_tag": "security_attendance.posting_console"})
        self.assertEqual(payload["step"]["title"], "Open ABC Mall's sheet for %s" % fields.Date.to_string(self.today))

        # The employee creates and generates the sheet in the console.
        batch = self.env["security.attendance.batch"].with_user(self.ops_user).create({
            "attendance_date": self.today, "site_id": self.site.id,
        })
        batch.action_generate_from_roster()
        payload = Session.report_ui_state({"client_tag": "security_attendance.posting_console"})
        self.assertEqual(payload["step"]["title"], "Mark every guard, then save")

        # Marks two of three: not done yet.
        records = batch.attendance_record_ids
        batch.action_bulk_mark_attendance([{"record_id": r.id, "manual_presence": "present"} for r in records[:2]])
        payload = Session.report_ui_state({"client_tag": "security_attendance.posting_console"})
        self.assertEqual(payload["state"], "active")
        self.assertEqual(self.register.state, "in_progress")

        batch.action_bulk_mark_attendance([{"record_id": records[2].id, "manual_presence": "awol"}])
        payload = Session.report_ui_state({"client_tag": "security_attendance.posting_console"})
        self.assertEqual(payload["state"], "completed")
        self.assertEqual(self.register.state, "submitted", "done because the records say so")
        self.confirm.invalidate_recordset(["readiness"])
        self.assertEqual(self.confirm.readiness, "ready", "Admin can now act")

    def test_confirm_and_verify_complete_from_the_real_review_and_lock(self):
        batch = self.env["security.attendance.batch"].with_user(self.ops_user).create({
            "attendance_date": self.today, "site_id": self.site.id,
        })
        batch.action_generate_from_roster()
        batch.action_bulk_mark_attendance([{"record_id": r.id, "manual_presence": "present"} for r in batch.attendance_record_ids])
        batch.with_user(self.admin_user).action_review()
        self.assertEqual(self.register.state, "verified", "confirmed by the next person")
        self.assertEqual(self.confirm.state, "submitted")
        batch.with_user(self.hr_user).action_lock()
        self.assertEqual((self.confirm.state, self.verify.state), ("verified", "verified"))

        team = self.env["security.work.task"].with_user(self.gm_user).get_team_today()
        cells = team["pipeline"][0]["cells"]
        self.assertTrue(all(c["state"] == "verified" for c in cells.values()))

    def test_only_hr_or_management_can_lock(self):
        batch = self.env["security.attendance.batch"].create({"attendance_date": self.today, "site_id": self.site.id})
        with self.assertRaises(Exception):
            batch.with_user(self.ops_user).action_lock()

    def test_overdue_work_becomes_an_exception_and_resolves_when_done(self):
        self.register.sudo().write({"due_at": fields.Datetime.now() - timedelta(hours=2)})
        self.env["security.work.task"].action_sweep_overdue()
        note = self.env["security.notification"].search([
            ("notification_type", "=", "task_overdue"), ("related_id", "=", self.register.id),
        ])
        self.assertEqual(len(note), 1)
        self.assertIn("Owner: Ops Supervisor", note.body)
        self.assertIn("Why it matters", note.body)
        self.env["security.exception.instance"].action_sync_from_notifications()
        exc = self.env["security.exception.instance"].search([("notification_id", "=", note.id)])
        self.assertEqual(exc.tier, "attention")

        self.env["security.work.task"].action_sweep_overdue()
        self.assertEqual(self.env["security.notification"].search_count([
            ("notification_type", "=", "task_overdue"), ("related_id", "=", self.register.id)]), 1, "no duplicates")

        self.register.sudo().action_submit()
        self.assertEqual(note.state, "dismissed")

    def test_segregation_is_enforced_in_setup(self):
        with self.assertRaises(Exception):
            self.env["security.deployguard.pipeline.setup"].create({
                "register_employee_id": self.ops.id, "confirm_employee_id": self.ops.id, "verify_employee_id": self.hr.id,
            })
