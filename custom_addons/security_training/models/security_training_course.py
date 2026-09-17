from odoo import api, fields, models
from odoo.exceptions import UserError

VERSION_STATES = [
    ("draft", "Draft"),
    ("in_review", "In Review"),
    ("published", "Published"),
    ("archived", "Archived"),
]


class SecurityTrainingCourse(models.Model):
    """A course is the stable identity; content lives on its versions.
    Publishing a new version never touches an in-flight assignment, which
    pins to a specific version_id (see security_training_assignment.py)."""

    _name = "security.training.course"
    _description = "Training Course"
    _order = "sequence, name"

    name = fields.Char(required=True)
    code = fields.Char(help="Stable machine key, e.g. 'using-erp-basics'.")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text()

    # Optional: if set, completing this course grants a certification of
    # this type (security.training.competency._grant links to it rather
    # than duplicating certification data).
    grants_certification_id = fields.Many2one("security.certification")

    version_ids = fields.One2many("security.training.course.version", "course_id", string="Versions")
    published_version_id = fields.Many2one(
        "security.training.course.version", compute="_compute_published_version_id", store=True,
        string="Current Published Version",
    )
    version_count = fields.Integer(compute="_compute_version_count")

    _code_unique = models.Constraint("unique(code)", "A course with this code already exists.")

    @api.depends("version_ids.state")
    def _compute_published_version_id(self):
        for course in self:
            course.published_version_id = course.version_ids.filtered(
                lambda v: v.state == "published"
            )[:1]

    def _compute_version_count(self):
        for course in self:
            course.version_count = len(course.version_ids)


class SecurityTrainingCourseVersion(models.Model):
    _name = "security.training.course.version"
    _description = "Training Course Version"
    _order = "course_id, version_number desc"

    course_id = fields.Many2one("security.training.course", required=True, ondelete="cascade")
    version_number = fields.Integer(required=True, default=1)
    name = fields.Char(compute="_compute_name", store=True)
    state = fields.Selection(VERSION_STATES, default="draft", required=True, tracking=True)

    section_ids = fields.One2many("security.training.section", "course_version_id", string="Sections")
    assessment_ids = fields.One2many("security.training.assessment", "course_version_id", string="Assessments")

    submitted_by_id = fields.Many2one("res.users", readonly=True)
    approved_by_id = fields.Many2one("res.users", readonly=True)
    approved_at = fields.Datetime(readonly=True)

    _course_version_unique = models.Constraint(
        "unique(course_id, version_number)", "This version number already exists for this course."
    )

    @api.depends("course_id.name", "version_number")
    def _compute_name(self):
        for v in self:
            v.name = f"{v.course_id.name} v{v.version_number}" if v.course_id else f"v{v.version_number}"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "version_number" not in vals and vals.get("course_id"):
                existing = self.search([("course_id", "=", vals["course_id"])], order="version_number desc", limit=1)
                vals["version_number"] = (existing.version_number + 1) if existing else 1
        return super().create(vals_list)

    def action_submit_for_review(self):
        for v in self:
            if v.state != "draft":
                raise UserError("Only a draft version can be submitted for review.")
            if not v.section_ids:
                raise UserError("Add at least one section before submitting for review.")
        self.write({"state": "in_review", "submitted_by_id": self.env.uid})

    def action_approve(self):
        """The named-approver rule (BUILD-STATUS-AND-PHASE-PLAN.md Phase
        4.4): whoever submitted a version for review cannot also approve
        it -- mirrors the front-desk self-review block added to
        security_attendance in Phase 3."""
        if not self.env.user.has_group("security_training.group_training_supervisor"):
            raise UserError("Only a training supervisor can approve a course version.")
        for v in self:
            if v.state != "in_review":
                raise UserError("Only a version in review can be approved.")
            if v.submitted_by_id and v.submitted_by_id.id == self.env.uid:
                raise UserError("You submitted this version for review, so you cannot also approve it.")
        self.write({
            "state": "published",
            "approved_by_id": self.env.uid,
            "approved_at": fields.Datetime.now(),
        })
        # Publishing a new version does not touch existing assignments --
        # each one already pinned its own version_id at creation.
        for v in self:
            v.course_id.version_ids.filtered(
                lambda other: other.id != v.id and other.state == "published"
            ).write({"state": "archived"})

    def action_reject(self):
        for v in self:
            if v.state != "in_review":
                raise UserError("Only a version in review can be sent back to draft.")
        self.write({"state": "draft"})

    def action_archive_version(self):
        self.write({"state": "archived"})


class SecurityTrainingSection(models.Model):
    _name = "security.training.section"
    _description = "Training Section"
    _order = "course_version_id, sequence, id"

    course_version_id = fields.Many2one("security.training.course.version", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    lesson_ids = fields.One2many("security.training.lesson", "section_id", string="Lessons")


class SecurityTrainingLesson(models.Model):
    _name = "security.training.lesson"
    _description = "Training Lesson"
    _order = "section_id, sequence, id"

    section_id = fields.Many2one("security.training.section", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    content_type = fields.Selection(
        [("text", "Text"), ("video_url", "Video (URL)")], default="text", required=True
    )
    body = fields.Html(string="Content", help="Used when content_type is 'text'.")
    video_url = fields.Char(help="Used when content_type is 'video_url'.")
