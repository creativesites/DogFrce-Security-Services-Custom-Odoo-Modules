from odoo import api, fields, models
from odoo.exceptions import UserError

# docs/deployguard/16-security-architecture.md §9 (Transparency): "A monitoring
# notice is shown at first sign-in and acknowledged (PolicyAcknowledgement)".
#
# The text lives here, next to its version, so the version on an
# acknowledgement always identifies exactly what the person was shown.
# Changing any word means bumping NOTICE_VERSION -- everyone is then asked
# again, and the old acknowledgements stay as a record of the old text.
#
# DRAFT pending the privacy/legal review (BUILD-STATUS-AND-PHASE-PLAN.md 5.1).
# Every statement below is true of the code as it stands; do not add a
# promise here that the software doesn't keep.
NOTICE_VERSION = "2026-09-draft-2"
NOTICE_TITLE = "How DeployGuard uses your activity"
NOTICE_BODY = [
    "DeployGuard records the work you do in it: tasks and checklists you "
    "complete, training you finish, and attendance you post. It compares "
    "that with the work expected of your role.",
    "This is used to find where the system, your training or your workload "
    "is letting you down, so you can get help. It is not a disciplinary tool, "
    "and it is not copied into HR or disciplinary records.",
    "You can see your own figures, and exactly what they are based on, in the "
    "app at any time. Approved leave and days you weren't rostered never count "
    "against you.",
    "If you have questions or concerns, speak to your supervisor or HR.",
]


class SecurityDeployguardPolicyAcknowledgement(models.Model):
    _name = "security.deployguard.policy.acknowledgement"
    _description = "DeployGuard Monitoring Notice Acknowledgement"
    _order = "acknowledged_at desc, id desc"

    # restrict, not cascade: this is evidence the person was told. Users are
    # archived in practice, and losing that evidence silently is worse than
    # blocking an outright delete.
    user_id = fields.Many2one("res.users", required=True, index=True, ondelete="restrict")
    notice_version = fields.Char(required=True, index=True)
    acknowledged_at = fields.Datetime(required=True, default=fields.Datetime.now)
    client = fields.Char(help="What the person acknowledged it in, e.g. 'DeployGuard Desktop 0.1.0 (Windows 11)'.")

    _user_version_unique = models.Constraint(
        "unique(user_id, notice_version)",
        "This notice version has already been acknowledged by this user.",
    )

    @api.model
    def get_notice(self):
        """The current notice and whether the calling user has acknowledged it."""
        ack = self.sudo().search([
            ("user_id", "=", self.env.uid), ("notice_version", "=", NOTICE_VERSION),
        ], limit=1)
        return {
            "version": NOTICE_VERSION,
            "title": NOTICE_TITLE,
            "body": NOTICE_BODY,
            "acknowledged": bool(ack),
            "acknowledged_at": fields.Datetime.to_string(ack.acknowledged_at) if ack else False,
        }

    @api.model
    def acknowledge(self, notice_version, client=None):
        """Always for the calling user -- there's deliberately no way to
        acknowledge on someone else's behalf. Refuses a stale version so an
        app showing old text can't record agreement to new text."""
        if notice_version != NOTICE_VERSION:
            raise UserError(
                "This notice has been updated since it was shown to you. Please read the new version."
            )
        existing = self.sudo().search([
            ("user_id", "=", self.env.uid), ("notice_version", "=", NOTICE_VERSION),
        ], limit=1)
        if not existing:
            existing = self.sudo().create({
                "user_id": self.env.uid,
                "notice_version": NOTICE_VERSION,
                "client": (client or "")[:120],
            })
        return self.get_notice()
