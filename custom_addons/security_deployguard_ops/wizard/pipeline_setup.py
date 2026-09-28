from odoo import api, fields, models
from odoo.exceptions import UserError


class DeployGuardPipelineSetup(models.TransientModel):
    """One screen for the GM: who registers, who confirms, who verifies
    attendance, and by when. Creates (or updates) the three linked
    responsibilities, and from then on the roster creates everyone's tasks."""

    _name = "security.deployguard.pipeline.setup"
    _description = "Set up the attendance pipeline"

    register_employee_id = fields.Many2one("hr.employee", string="Registers attendance", required=True,
                                           help="DogForce: the Operations Supervisor.")
    register_due = fields.Float(default=10.0, string="Registered by")
    confirm_employee_id = fields.Many2one("hr.employee", string="Confirms attendance", required=True,
                                          help="DogForce: Admin. Must be a different person from whoever registers.")
    confirm_due = fields.Float(default=12.0, string="Confirmed by")
    verify_employee_id = fields.Many2one("hr.employee", string="Verifies attendance", required=True,
                                         help="DogForce: HR.")
    verify_due = fields.Float(default=15.0, string="Verified by")
    site_ids = fields.Many2many("security.client.site", string="Only these sites", help="Empty: every rostered site.")

    @api.constrains("register_employee_id", "confirm_employee_id")
    def _check_segregation(self):
        for wiz in self:
            if wiz.register_employee_id == wiz.confirm_employee_id:
                raise UserError(self.env._(
                    "The person who registers attendance can't also confirm it. The Posting Console refuses "
                    "self-review, so their Confirm task could never be done."
                ))

    def _upsert(self, code, vals):
        Resp = self.env["security.work.responsibility"].with_context(active_test=False)
        template = self.env.ref(f"security_deployguard_ops.template_attendance_{code}")
        resp = Resp.search([("checklist_template_id", "=", template.id)], limit=1)
        vals = dict(vals, checklist_template_id=template.id, active=True, site_ids=[(6, 0, self.site_ids.ids)])
        if resp:
            resp.write(vals)
        else:
            resp = Resp.create(vals)
        return resp

    def action_apply(self):
        self.ensure_one()
        course = self.env.ref("security_deployguard_ops.course_daily_attendance", raise_if_not_found=False)
        common = {"trigger": "rostered_site_day", "required_course_id": course.id if course else False,
                  "odoo_path": "/odoo/action-security_attendance.action_attendance_posting_console"}
        register = self._upsert("register", dict(
            common, name="Register attendance", sequence=10, employee_id=self.register_employee_id.id,
            due_hour=self.register_due, completes_at_stage="marked", guidance_flow_code="attendance_register",
            depends_on_id=False, task_name_template="Register attendance · {site}",
            why_it_matters="Payroll, client billing and AWOL follow-up are worked out from this register. "
                           "If it's missing, guards may be paid wrongly and clients billed wrongly.",
        ))
        confirm = self._upsert("confirm", dict(
            common, name="Confirm attendance", sequence=20, employee_id=self.confirm_employee_id.id,
            due_hour=self.confirm_due, completes_at_stage="reviewed", guidance_flow_code="attendance_confirm",
            depends_on_id=register.id, task_name_template="Confirm attendance · {site}",
            why_it_matters="A second person checking the register catches mistakes before they reach payroll.",
        ))
        verify = self._upsert("verify", dict(
            common, name="Verify attendance", sequence=30, employee_id=self.verify_employee_id.id,
            due_hour=self.verify_due, completes_at_stage="locked", guidance_flow_code="attendance_verify",
            depends_on_id=confirm.id, task_name_template="Verify attendance · {site}",
            odoo_path="/odoo/action-security_attendance.action_security_attendance_batch",
            why_it_matters="Locking is what payroll reads from. It's the last check before people are paid.",
        ))
        (register | confirm | verify).action_materialize_all()
        return {
            "type": "ir.actions.act_window",
            "res_model": "security.work.responsibility",
            "view_mode": "list,form",
            "domain": [("id", "in", (register | confirm | verify).ids)],
            "name": self.env._("Attendance pipeline"),
        }
