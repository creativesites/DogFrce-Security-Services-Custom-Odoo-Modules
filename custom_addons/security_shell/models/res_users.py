from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        if "action_id" in fields_list and not vals.get("action_id"):
            action = self.env.ref(
                "security_base.action_deployguard_main_command_center",
                raise_if_not_found=False,
            )
            if action:
                vals["action_id"] = action.id
        return vals
