from odoo import api, fields, models, _


class SecurityClientSite(models.Model):
    _inherit = "security.client.site"

    latest_client_rating = fields.Selection([
        ("1", "1 Star - Poor"),
        ("2", "2 Stars - Fair"),
        ("3", "3 Stars - Good"),
        ("4", "4 Stars - Very Good"),
        ("5", "5 Stars - Excellent"),
    ], string="Latest Client Rating")
    latest_client_feedback = fields.Text(string="Latest Client Feedback")
    latest_client_feedback_date = fields.Date(string="Latest Feedback Date")


class SecurityPortalBridge(models.AbstractModel):
    _name = "security.portal.bridge"
    _description = "Client Portal Operations and CRM Bridge"

    @api.model
    def _handle_bus_event(self, event_name, source_model, source_id, payload):
        """
        Listens for client feedback events on the central intelligence bus, and immediately
        triggers recalculations of the CRM Lead's health, compliance ratings, and risk levels.
        """
        if event_name == "portal.feedback_received":
            site_id = payload.get("site_id")
            rating = int(payload.get("rating", 5))
            feedback = payload.get("feedback", "")

            site = self.env["security.client.site"].browse(site_id)
            if not site:
                return

            # Register the feedback details on the site
            site.write({
                "latest_client_rating": str(rating),
                "latest_client_feedback": feedback,
                "latest_client_feedback_date": fields.Date.today(),
            })

            # Fetch associated CRM leads linking this client/site
            if "crm.lead" in self.env:
                leads = self.env["crm.lead"].search([
                    "|",
                    ("partner_id", "=", site.partner_id.id),
                    ("partner_id", "=", site.partner_id.parent_id.id),
                ])
                for lead in leads:
                    if hasattr(lead, "recalculate_operational_health"):
                        lead.recalculate_operational_health()
