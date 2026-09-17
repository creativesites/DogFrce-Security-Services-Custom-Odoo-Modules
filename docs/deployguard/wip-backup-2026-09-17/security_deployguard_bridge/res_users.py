from odoo import models, fields


class ResUsers(models.Model):
    _inherit = "res.users"

    deployguard_access = fields.Boolean(
        string="DeployGuard Access",
        default=False,
        help="Whether this user is permitted to sign in to the DeployGuard Platform.",
    )
