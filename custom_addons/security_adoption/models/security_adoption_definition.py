from odoo import fields, models

WORKFLOW_KEYS = [
    ("attendance.post", "Attendance posting"),
    ("incident.review", "Incident review"),
    ("site.visit", "Site visit"),
    ("training.mandatory", "Mandatory training"),
    ("shift.handover", "Shift handover"),
]


class SecurityAdoptionExpectedWorkDefinition(models.Model):
    """Tenant configuration for one MVP workflow_key (docs/deployguard/
    09-adoption-engine.md §2). Deliberately has no generic "applies_to
    role/scope" field: each of the five workflows resolves who it applies
    to differently (site supervisor, incident reviewer, all desktop
    users...), and that resolution lives in
    security.adoption.expected.work.item's per-workflow materialisers in
    Python, against real domain models, rather than being flattened into
    a one-size-fits-all config field that can't actually express it."""

    _name = "security.adoption.expected.work.definition"
    _description = "Adoption: Expected Work Definition"
    _order = "workflow_key"

    workflow_key = fields.Selection(WORKFLOW_KEYS, required=True)
    name = fields.Char(compute="_compute_name", store=True)
    cadence_description = fields.Char(
        required=True,
        help="Informational only -- the actual cadence logic lives in "
             "security.adoption.expected.work.item's materialiser for "
             "this workflow_key.",
    )
    weight = fields.Float(default=1.0, help="Relative importance if a tenant runs more than one instance of a workflow_key -- unused by the MVP's single-instance-per-key setup, kept per spec §2.")
    active = fields.Boolean(default=True)

    _workflow_key_unique = models.Constraint(
        "unique(workflow_key)",
        "Only one Expected Work Definition per workflow_key.",
    )

    def _compute_name(self):
        labels = dict(WORKFLOW_KEYS)
        for definition in self:
            definition.name = labels.get(definition.workflow_key, definition.workflow_key)
