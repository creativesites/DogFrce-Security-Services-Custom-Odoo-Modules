from odoo import api, fields, models
from odoo.osv import expression


class SecurityHelpCategory(models.Model):
    _name = "security.help.category"
    _description = "Help Category"
    _order = "sequence, name"

    name = fields.Char(required=True)
    icon = fields.Char(default="fa-book", help="Font Awesome class, e.g. fa-user")
    color = fields.Char(default="#1a3a5c", help="Hex colour for the icon badge")
    sequence = fields.Integer(default=10)
    country_code = fields.Char(
        help="Leave blank to show for all countries. Set to e.g. 'ZM' to show only for Zambia companies.",
    )
    article_ids = fields.One2many("security.help.article", "category_id", string="Articles")
    article_count = fields.Integer(compute="_compute_article_count")

    @api.depends("article_ids")
    def _compute_article_count(self):
        for cat in self:
            cat.article_count = len(cat.article_ids)


class SecurityHelpArticle(models.Model):
    _name = "security.help.article"
    _description = "Help Article"
    _order = "sequence, title"

    category_id = fields.Many2one("security.help.category", required=True, ondelete="cascade")
    title = fields.Char(required=True)
    summary = fields.Char(help="One-line description shown in the article list")
    body = fields.Html(required=True, sanitize=False)
    sequence = fields.Integer(default=10)
    tags = fields.Char(help="Space-separated keywords for search")
    country_code = fields.Char(
        help="Leave blank to show for all countries. Set to e.g. 'ZM' to show only for Zambia companies.",
    )

    @api.model
    def get_company_country_code(self):
        """Return the current company's ISO country code for the help portal."""
        return self.env.company.country_id.code or ""

    @api.model
    def search_articles(self, query, country_code=None):
        """Full-text search across title, summary, and tags, filtered by country."""
        if not query or not query.strip():
            return []
        q = query.strip().lower()
        text_domain = expression.OR([
            [("title", "ilike", q)],
            [("summary", "ilike", q)],
            [("tags", "ilike", q)],
        ])
        if country_code:
            country_domain = expression.OR([
                [("country_code", "=", False)],
                [("country_code", "=", country_code)],
            ])
            domain = expression.AND([country_domain, text_domain])
        else:
            domain = text_domain
        return self.search_read(domain, ["id", "title", "summary", "category_id"], limit=20)
