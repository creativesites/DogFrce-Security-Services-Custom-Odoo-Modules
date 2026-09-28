import json

from odoo import api, fields, models
from odoo.exceptions import ValidationError


def _json_field_check(value, expected_type, label):
    if not value:
        return
    try:
        parsed = json.loads(value)
    except ValueError as exc:
        raise ValidationError(f"{label} must be valid JSON: {exc}") from exc
    if not isinstance(parsed, expected_type):
        raise ValidationError(f"{label} has the wrong JSON shape.")


class SecurityGuidanceFlow(models.Model):
    """A guided task: the approved, step-by-step way to do one piece of work
    in the ERP. Authored as data by people who know the procedure. AI never
    writes or changes a flow."""

    _name = "security.guidance.flow"
    _description = "Guided Task Flow"
    _order = "name"

    code = fields.Char(required=True, index=True, help="Stable key referenced by responsibilities and lessons.")
    name = fields.Char(required=True)
    objective = fields.Text(help="One sentence: what the employee will have done at the end.")
    why = fields.Text(help="Why this work exists. Shown at the start.")
    active = fields.Boolean(default=True)
    step_ids = fields.One2many("security.guidance.step", "flow_id", string="Steps")
    step_count = fields.Integer(compute="_compute_step_count")

    _code_unique = models.Constraint("unique(code)", "A guided task with this code already exists.")

    @api.depends("step_ids")
    def _compute_step_count(self):
        for flow in self:
            flow.step_count = len(flow.step_ids)


class SecurityGuidanceStep(models.Model):
    """One step of a flow.

    - `where`: the ERP screen where the step is done. The employee is
      "off track" when elsewhere, and `deviation_hint` says how to get back.
    - `target`: ordered anchors for the control to highlight. Stable
      `data-dg-anchor` attributes and Odoo menu xmlids / button names come
      first, visible text last. Never coordinates.
    - `done_ui`: a screen reached, which counts as done once reached.
    - `done_check`: a server check against real records, re-evaluated every
      time, so it is the truth. Implemented as `_guidance_check_<name>` on
      security.guidance.session by the module that knows the data.
    """

    _name = "security.guidance.step"
    _description = "Guided Task Step"
    _order = "flow_id, sequence, id"

    flow_id = fields.Many2one("security.guidance.flow", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, string="Title")
    instruction = fields.Text(required=True, help="What to do, in plain words. {site} and {date} are filled in.")
    why = fields.Text(help="Why this step matters.")
    help_html = fields.Html(string="Help", help="Shown when the employee says they're stuck.")
    success_message = fields.Char()
    deviation_hint = fields.Char(help="How to get back to where this step happens.")
    where_json = fields.Text(string="Where (JSON)", help='e.g. {"client_tag": "security_attendance.posting_console"}')
    target_json = fields.Text(string="Highlight (JSON)", help='e.g. [{"anchor": "pc-save"}, {"text": "Save Changes", "selector": "button"}]')
    done_ui_json = fields.Text(string="Done when screen (JSON)")
    done_check = fields.Char(string="Done when check", help="Name of a server check, e.g. attendance_all_marked.")

    @api.constrains("where_json", "target_json", "done_ui_json")
    def _check_json(self):
        for step in self:
            _json_field_check(step.where_json, (dict, list), "Where")
            _json_field_check(step.target_json, list, "Highlight")
            _json_field_check(step.done_ui_json, (dict, list), "Done when screen")

    def _json(self, fname, default):
        self.ensure_one()
        raw = self[fname]
        return json.loads(raw) if raw else default
