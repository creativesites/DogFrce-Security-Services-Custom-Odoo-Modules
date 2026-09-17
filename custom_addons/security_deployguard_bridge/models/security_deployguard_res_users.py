from odoo import fields, models


class ResUsers(models.Model):
    """The per-user "DeployGuard access" flag from DG-ADR-018 §6.

    Not exposed on the standard Preferences form (it's an integration
    concern, not something a user sets for themselves) -- only on the
    DeployGuard Bridge configuration page and via get_users() for the
    Platform's identity linking. Nothing in this slice enforces this flag
    yet (that's the auth/SSO endpoints, DG-ADR-007 -- not built here); it
    exists now so identity linking and the facade have something real to
    read once they do.
    """

    _inherit = "res.users"

    deployguard_access = fields.Boolean(
        string="DeployGuard Access",
        default=False,
        groups="security_deployguard_bridge.group_deployguard_integration,base.group_system",
        help="Whether this user may sign in to the DeployGuard Platform. "
             "Has no effect yet -- the auth/SSO endpoints that check it are "
             "not built (see security_deployguard_bridge's manifest).",
    )
