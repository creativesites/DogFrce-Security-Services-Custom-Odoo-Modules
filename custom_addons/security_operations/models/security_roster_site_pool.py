# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SecurityRosterBatchSitePool(models.Model):
    _name = "security.roster.batch.site.pool"
    _description = "Roster Cycle Site Guard Team Snapshot & Overrides"
    _order = "batch_id desc, site_id asc"

    batch_id = fields.Many2one(
        "security.roster.batch",
        string="Roster Batch",
        required=True,
        ondelete="cascade",
        index=True,
    )
    site_id = fields.Many2one(
        "security.client.site",
        string="Client Site",
        required=True,
        ondelete="cascade",
        index=True,
    )
    guard_ids = fields.Many2many(
        "hr.employee",
        "security_roster_batch_site_pool_guard_rel",
        "pool_id",
        "employee_id",
        string="Roster Guards",
        domain=[("security_guard", "=", True), ("active", "=", True)],
        help="Effective guard pool for this site during this specific roster cycle.",
    )
    guard_pool_mode = fields.Selection(
        [
            ("site_only", "Regular Site Pool Only"),
            ("site_then_relief", "Site Pool with Relief Fallback"),
        ],
        string="Guard Pool Mode",
        default="site_only",
        required=True,
    )
    added_guard_ids = fields.Many2many(
        "hr.employee",
        "security_roster_batch_site_pool_added_rel",
        "pool_id",
        "employee_id",
        string="Temporary Additions",
        help="Guards temporarily added to this site for this roster cycle only.",
    )
    removed_guard_ids = fields.Many2many(
        "hr.employee",
        "security_roster_batch_site_pool_removed_rel",
        "pool_id",
        "employee_id",
        string="Temporary Exclusions",
        help="Guards temporarily removed from this site for this roster cycle only.",
    )
    guard_count = fields.Integer(string="Roster Guard Count", compute="_compute_guard_count")
    is_modified_from_defaults = fields.Boolean(
        string="Modified from Site Defaults",
        compute="_compute_is_modified_from_defaults",
    )

    _sql_constraints = [
        ("batch_site_unique", "unique(batch_id, site_id)", "Each site can only have one team pool per roster batch.")
    ]

    @api.depends("guard_ids")
    def _compute_guard_count(self):
        for pool in self:
            pool.guard_count = len(pool.guard_ids)

    @api.depends("guard_ids", "site_id.site_guard_pool_ids", "guard_pool_mode", "site_id.guard_pool_mode")
    def _compute_is_modified_from_defaults(self):
        for pool in self:
            if not pool.site_id:
                pool.is_modified_from_defaults = False
                continue
            default_guards = set(pool.site_id.site_guard_pool_ids.ids)
            current_guards = set(pool.guard_ids.ids)
            pool.is_modified_from_defaults = (
                default_guards != current_guards or pool.guard_pool_mode != pool.site_id.guard_pool_mode
            )

    def action_reset_to_site_defaults(self):
        """Reset roster pool to match the site's permanent defaults."""
        for pool in self:
            pool.guard_ids = [(6, 0, pool.site_id.site_guard_pool_ids.ids)]
            pool.guard_pool_mode = pool.site_id.guard_pool_mode or "site_only"
            pool.added_guard_ids = [(5, 0, 0)]
            pool.removed_guard_ids = [(5, 0, 0)]
        return True

    def action_save_as_site_defaults(self):
        """Explicitly promote this cycle's team to become the permanent site defaults."""
        for pool in self:
            pool.site_id.site_guard_pool_ids = [(6, 0, pool.guard_ids.ids)]
            pool.site_id.guard_pool_mode = pool.guard_pool_mode
            pool.site_id.guard_pool_source = f"Saved from Roster {pool.batch_id.name}"
            pool.site_id.guard_pool_source_date = fields.Date.today()
            pool.added_guard_ids = [(5, 0, 0)]
            pool.removed_guard_ids = [(5, 0, 0)]
            if hasattr(pool.site_id, "message_post"):
                guard_names = ", ".join(pool.guard_ids.mapped("name"))
                pool.site_id.message_post(
                    body=f"<b>Regular Site Guards Updated from Roster</b>: {pool.batch_id.name}<br/>"
                         f"Guards ({len(pool.guard_ids)}): {guard_names}<br/>"
                         f"Mode: {pool.guard_pool_mode}"
                )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Saved as Site Defaults"),
                "message": _("Regular site guard team updated permanently for %s.") % pool.site_id.name,
                "type": "success",
                "sticky": False,
            }
        }
