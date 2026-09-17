from odoo import api, fields, models
from odoo.exceptions import UserError

# The roles that must account for a roster, in the order they appear on the
# batch. Operations does not appear here: Operations *is* the author, and the
# roster they draft is the operative roster (docs/ROSTERING_SIMPLIFICATION_PLAN.md
# §3). Everyone below signs off on a roster that is already live.
SIGNOFF_ROLES = [
    ("front_desk", "Front Desk"),
    ("general_manager", "General Manager"),
    ("hr", "HR"),
    ("finance", "Finance"),
    ("director", "Director"),
]

ROLE_GROUP = {
    "front_desk": "security_operations.group_security_front_desk",
    "general_manager": "security_base.group_security_manager",
    "hr": "security_base.group_security_hr_payroll_officer",
    "finance": "security_operations.group_security_finance",
    "director": "security_base.group_security_owner",
}


class SecurityRosterSignoff(models.Model):
    """A role's accountability for a roster that is already operating.

    Deliberately NOT a gate. The roster Operations drafts is the roster the
    company works to; these sign-offs record that each role has checked their
    part of it. A missing sign-off is visible and chaseable, but it never stops
    a guard being posted -- which is what "non-blocking" has to mean if the
    business is not to stall behind a checkbox.
    """

    _name = "security.roster.signoff"
    _description = "Roster Sign-Off"
    _order = "batch_id, sequence"

    batch_id = fields.Many2one(
        "security.roster.batch", required=True, ondelete="cascade", index=True
    )
    role = fields.Selection(SIGNOFF_ROLES, required=True)
    sequence = fields.Integer(default=10)

    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("signed", "Signed off"),
            ("flagged", "Flagged"),
        ],
        default="pending",
        required=True,
        index=True,
    )

    user_id = fields.Many2one("res.users", string="Signed by", readonly=True)
    signed_at = fields.Datetime(readonly=True)
    note = fields.Char(string="Comment")

    can_sign = fields.Boolean(compute="_compute_can_sign")

    _sql_constraints = [
        (
            "unique_role_per_batch",
            "unique(batch_id, role)",
            "Each role signs a roster batch once.",
        )
    ]

    @api.depends("role")
    def _compute_can_sign(self):
        """Whether the current user holds the role this row is waiting on."""
        for rec in self:
            group = ROLE_GROUP.get(rec.role)
            rec.can_sign = bool(group) and self.env.user.has_group(group)

    def _assert_can_sign(self):
        for rec in self:
            if not rec.can_sign:
                raise UserError(
                    f"You are not in the {dict(SIGNOFF_ROLES)[rec.role]} role, "
                    "so you cannot sign off on its behalf."
                )

    def action_sign(self):
        self._assert_can_sign()
        self.write({
            "state": "signed",
            "user_id": self.env.user.id,
            "signed_at": fields.Datetime.now(),
        })
        return True

    def action_flag(self):
        """Raise a concern without stopping the roster.

        The roster keeps running; the flag is what gets chased.
        """
        self._assert_can_sign()
        for rec in self:
            if not rec.note:
                raise UserError(
                    "Say what the problem is before flagging, so whoever picks "
                    "it up knows what to fix."
                )
        self.write({
            "state": "flagged",
            "user_id": self.env.user.id,
            "signed_at": fields.Datetime.now(),
        })
        return True

    def action_reset(self):
        self._assert_can_sign()
        self.write({"state": "pending", "user_id": False, "signed_at": False})
        return True


class SecurityRosterBatchSignoff(models.Model):
    _inherit = "security.roster.batch"

    signoff_ids = fields.One2many(
        "security.roster.signoff", "batch_id", string="Sign-offs"
    )
    signoff_pending_count = fields.Integer(
        compute="_compute_signoff_progress", string="Awaiting sign-off"
    )
    signoff_flagged_count = fields.Integer(
        compute="_compute_signoff_progress", string="Flagged"
    )
    signoff_summary = fields.Char(
        compute="_compute_signoff_progress", string="Sign-off status"
    )

    @api.depends("signoff_ids.state")
    def _compute_signoff_progress(self):
        for batch in self:
            pending = batch.signoff_ids.filtered(lambda s: s.state == "pending")
            flagged = batch.signoff_ids.filtered(lambda s: s.state == "flagged")
            batch.signoff_pending_count = len(pending)
            batch.signoff_flagged_count = len(flagged)

            if not batch.signoff_ids:
                batch.signoff_summary = "No sign-offs raised yet"
            elif flagged:
                names = ", ".join(dict(SIGNOFF_ROLES)[s.role] for s in flagged)
                batch.signoff_summary = f"Flagged by {names}"
            elif pending:
                names = ", ".join(dict(SIGNOFF_ROLES)[s.role] for s in pending)
                batch.signoff_summary = f"Awaiting {names}"
            else:
                batch.signoff_summary = "All roles signed off"

    def _ensure_signoffs(self):
        """Create the pending sign-off rows for any role that has none yet."""
        Signoff = self.env["security.roster.signoff"]
        for batch in self:
            existing = set(batch.signoff_ids.mapped("role"))
            for index, (role, _label) in enumerate(SIGNOFF_ROLES):
                if role not in existing:
                    Signoff.create({
                        "batch_id": batch.id,
                        "role": role,
                        "sequence": (index + 1) * 10,
                    })

    def action_generate_slots(self):
        """Generating the roster is what makes it operative, so that is the
        point the sign-off sheet appears -- not an extra approval step."""
        result = super().action_generate_slots()
        self._ensure_signoffs()
        return result

    def action_open_signoffs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Sign-offs — {self.name}",
            "res_model": "security.roster.signoff",
            "view_mode": "list",
            "domain": [("batch_id", "=", self.id)],
            "context": {"default_batch_id": self.id},
        }
