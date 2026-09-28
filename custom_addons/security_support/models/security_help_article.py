from odoo import api, fields, models


class SecurityHelpArticle(models.Model):
    _inherit = "security.help.article"

    route = fields.Char(help="DeployGuard screen this article helps with, e.g. /work or /training.")
    workflow_key = fields.Char(help="Operational workflow this article explains, e.g. attendance.post.")

    @api.model
    def get_contextual_articles(self, route=None, workflow_key=None, limit=5):
        """Articles for the screen/workflow the employee is on, most specific
        first, topped up with general articles so the drawer is never empty
        when help exists."""
        limit = max(1, min(int(limit or 5), 20))
        fields_ = ["id", "title", "summary", "category_id", "route", "workflow_key"]
        found = self.browse()
        if workflow_key:
            found |= self.search([("workflow_key", "=", workflow_key)], limit=limit)
        if route and len(found) < limit:
            found |= self.search([("route", "=", route), ("id", "not in", found.ids)], limit=limit - len(found))
        if len(found) < limit:
            found |= self.search([("id", "not in", found.ids)], limit=limit - len(found))
        return found.read(fields_)
