from odoo import api, fields, models


class SecurityWorkResponsibility(models.Model):
    _inherit = "security.work.responsibility"

    required_course_id = fields.Many2one(
        "security.training.course", string="Learn first",
        help="Course the owner should complete before (or while) doing this duty. Today shows "
             "'Learn this first' until it's done. It never blocks the work itself.",
    )


class SecurityTrainingLesson(models.Model):
    _inherit = "security.training.lesson"

    guidance_flow_code = fields.Char(help="Guided task to practise this lesson in the real ERP ('Practice it now').")


class SecurityWorkTask(models.Model):
    _inherit = "security.work.task"

    @api.model
    def _course_done(self, employee, course):
        Assignment = self.env["security.training.assignment"].sudo()
        return bool(Assignment.search_count([
            ("employee_id", "=", employee.id), ("course_id", "=", course.id), ("state", "=", "completed"),
        ]))

    def _today_card(self):
        card = super()._today_card()
        course = self.responsibility_id.required_course_id
        if course:
            assignment = self.env["security.training.assignment"].sudo().search([
                ("employee_id", "=", self.employee_id.id), ("course_id", "=", course.id),
            ], order="id desc", limit=1)
            card["training"] = {
                "course_id": course.id,
                "course_name": course.name,
                "assignment_id": assignment.id or False,
                "done": assignment.state == "completed",
            }
        else:
            card["training"] = False
        return card
