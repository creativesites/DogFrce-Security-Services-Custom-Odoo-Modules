from odoo import api, fields, models


class SecurityTrainingCompetency(models.Model):
    """Evidence that an employee completed a course, linked to the EXISTING
    security.employee.certification model when the course maps to a real
    certification type (course.grants_certification_id) -- never a
    duplicate certification record of our own (BUILD-STATUS-AND-PHASE-
    PLAN.md Phase 4.3)."""

    _name = "security.training.competency"
    _description = "Training Competency"
    _order = "granted_at desc"

    employee_id = fields.Many2one("hr.employee", required=True, index=True)
    course_id = fields.Many2one("security.training.course", required=True)
    course_version_id = fields.Many2one("security.training.course.version", required=True)
    assignment_id = fields.Many2one("security.training.assignment", required=True, ondelete="cascade")
    granted_at = fields.Datetime(default=fields.Datetime.now, required=True)
    evidence_certification_id = fields.Many2one(
        "security.employee.certification", readonly=True,
        help="Set only when the course has a grants_certification_id -- "
             "points at a real certification record, never a duplicate.",
    )

    _assignment_unique = models.Constraint(
        "unique(assignment_id)", "A competency has already been granted for this assignment."
    )

    @api.model
    def _grant_from_assignment(self, assignment):
        self = self.sudo()
        if self.search_count([("assignment_id", "=", assignment.id)]):
            return self.browse()

        evidence_certification = False
        cert_type = assignment.course_id.grants_certification_id
        if cert_type:
            evidence_certification = self.env["security.employee.certification"].sudo().create({
                "employee_id": assignment.employee_id.id,
                "certification_id": cert_type.id,
                "issue_date": fields.Date.context_today(self),
                "note": f"Granted by completing training course '{assignment.course_id.name}'.",
            })

        return self.create({
            "employee_id": assignment.employee_id.id,
            "course_id": assignment.course_id.id,
            "course_version_id": assignment.course_version_id.id,
            "assignment_id": assignment.id,
            "evidence_certification_id": evidence_certification.id if evidence_certification else False,
        })
