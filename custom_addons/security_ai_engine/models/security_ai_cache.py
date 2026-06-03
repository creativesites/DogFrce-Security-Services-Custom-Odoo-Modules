from odoo import fields, models


class SecurityAICache(models.Model):
    """
    Short-lived cache for AI responses.

    When enabled, the engine hashes the (feature + system_prompt + user_message)
    tuple and skips the provider API call if a matching entry exists within the
    configured TTL window.  Saves API cost for repeated identical queries.
    """
    _name = "security.ai.cache"
    _description = "AI Response Cache"
    _order = "created_at desc"
    _rec_name = "feature"

    cache_key = fields.Char(
        required=True,
        index=True,
        help="SHA-256 hash of feature + system_prompt + user_message.",
    )
    feature = fields.Char(required=True)
    response = fields.Text(required=True)
    created_at = fields.Datetime(default=fields.Datetime.now, required=True)
    hit_count = fields.Integer(default=0, string="Cache Hits")

    _sql_constraints = [
        ("unique_cache_key", "UNIQUE(cache_key)", "Cache key must be unique."),
    ]

    def action_clear_all(self):
        """Delete every cache entry (available from the list view)."""
        self.search([]).unlink()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Cache Cleared",
                "message": "All cached AI responses have been removed.",
                "type": "success",
            },
        }
