from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError


class SecurityAIConfig(models.Model):
    _name = "security.ai.config"
    _description = "Security AI Engine Configuration"

    name = fields.Char(default="AI Engine Configuration", required=True)
    active = fields.Boolean(default=True)

    active_provider = fields.Selection(
        [
            ("claude", "Claude (Anthropic)"),
            ("openai", "OpenAI"),
            ("gemini", "Google Gemini"),
        ],
        string="Active Provider",
        default="claude",
        required=True,
    )
    claude_api_key = fields.Char(string="Anthropic API Key", password=True, copy=False)
    claude_model = fields.Char(
        string="Claude Model",
        default="claude-sonnet-4-6",
        help="e.g. claude-sonnet-4-6, claude-opus-4-8, claude-haiku-4-5",
    )
    openai_api_key = fields.Char(string="OpenAI API Key", password=True, copy=False)
    openai_model = fields.Char(
        string="OpenAI Model",
        default="gpt-4o",
        help="e.g. gpt-4o, gpt-4o-mini, o1",
    )
    gemini_api_key = fields.Char(string="Gemini API Key", password=True, copy=False)
    gemini_model = fields.Char(
        string="Gemini Model",
        default="gemini-2.5-flash",
        help="e.g. gemini-2.5-flash, gemini-2.0-flash, gemini-1.5-pro",
    )

    max_tokens = fields.Integer(
        default=4096,
        string="Max Tokens Per Call",
        help=(
            "Upper limit on response length. The structured JSON output format requires "
            "2000–4000 tokens for features that send large inputs (payslip records, "
            "attendance history). Recommended: 4096. Maximum: 8000."
        ),
    )
    temperature = fields.Float(
        default=0.2,
        string="Temperature",
        help="0.0 = deterministic, 1.0 = creative. 0.1–0.3 for analytical tasks.",
    )

    # Feature toggles
    feature_attendance_anomaly = fields.Boolean(default=True, string="Attendance Anomaly Detection")
    feature_risk_profiling = fields.Boolean(default=True, string="Guard Risk Profiling")
    feature_billing_auditor = fields.Boolean(default=True, string="Billing Auditor")
    feature_roster_optimizer = fields.Boolean(default=True, string="Roster Optimizer")
    feature_shift_fill = fields.Boolean(
        default=True,
        string="Smart Shift Fill",
        help="AI replacement guard suggestions when a guard is absent or AWOL.",
    )
    feature_incident_advisor = fields.Boolean(
        default=True,
        string="Incident Consequence Advisor",
        help="AI disciplinary consequence recommendations based on incident history.",
    )
    feature_leave_coverage = fields.Boolean(
        default=True,
        string="Leave Coverage Check",
        help="AI assessment of roster coverage impact before approving leave requests.",
    )
    feature_doc_renewal_letter = fields.Boolean(
        default=True,
        string="Document Renewal Letter",
        help="AI-drafted renewal notice for guards with expiring documents.",
    )
    feature_performance_review = fields.Boolean(
        default=True,
        string="Guard Performance Review",
        help="AI-generated quarterly performance review based on 90-day operational data.",
    )
    feature_payslip_explain = fields.Boolean(
        default=True,
        string="Payslip Plain-English Explanation",
        help="AI translation of payslip line items into plain language the guard can understand.",
    )

    # Response caching
    enable_response_cache = fields.Boolean(
        default=True,
        string="Enable Response Cache",
        help="Reuse AI responses for identical inputs within the TTL window, saving API cost.",
    )
    cache_ttl_hours = fields.Integer(
        default=24,
        string="Cache TTL (hours)",
        help="How long a cached response is considered fresh.",
    )

    # Multi-provider fallback
    fallback_provider = fields.Selection(
        [
            ("none",   "Disabled"),
            ("claude", "Claude (Anthropic)"),
            ("openai", "OpenAI"),
            ("gemini", "Google Gemini"),
        ],
        string="Fallback Provider",
        default="none",
        help="If the primary provider fails, retry with this provider using its configured API key.",
    )

    # Usage stats (computed from logs)
    total_calls = fields.Integer(compute="_compute_usage_stats", string="Total AI Calls")
    successful_calls = fields.Integer(compute="_compute_usage_stats", string="Successful")
    failed_calls = fields.Integer(compute="_compute_usage_stats", string="Failed")
    monthly_tokens_in = fields.Integer(compute="_compute_usage_stats", string="Tokens In (MTD)")
    monthly_tokens_out = fields.Integer(compute="_compute_usage_stats", string="Tokens Out (MTD)")
    monthly_cost_usd = fields.Float(
        compute="_compute_usage_stats",
        string="Estimated Cost USD (MTD)",
        digits=(10, 4),
    )

    def _compute_usage_stats(self):
        log_model = self.env["security.ai.log"]
        for config in self:
            logs = log_model.search([("config_id", "=", config.id)])
            config.total_calls = len(logs)
            config.successful_calls = len(logs.filtered(lambda l: l.state == "success"))
            config.failed_calls = len(logs.filtered(lambda l: l.state == "error"))

            # MTD stats
            month_start = fields.Date.today().replace(day=1)
            mtd_logs = logs.filtered(
                lambda l: l.call_date and l.call_date.date() >= month_start
                and l.state == "success"
            )
            config.monthly_tokens_in = sum(mtd_logs.mapped("tokens_in"))
            config.monthly_tokens_out = sum(mtd_logs.mapped("tokens_out"))
            config.monthly_cost_usd = sum(mtd_logs.mapped("estimated_cost_usd"))

    @api.constrains("temperature")
    def _check_temperature(self):
        for config in self:
            if not (0.0 <= config.temperature <= 1.0):
                raise ValidationError("Temperature must be between 0.0 and 1.0.")

    @api.constrains("max_tokens")
    def _check_max_tokens(self):
        for config in self:
            if config.max_tokens < 100 or config.max_tokens > 8000:
                raise ValidationError("Max tokens must be between 100 and 8000.")

    def action_test_connection(self):
        self.ensure_one()
        engine = self.env["security.ai.engine"]
        try:
            result = engine.complete(
                feature="__test__",
                system_prompt="You are a connectivity test agent.",
                user_message="Reply with exactly: CONNECTION_OK",
                config=self,
            )
            if result and "CONNECTION_OK" in result:
                return self._show_message("Connection successful", "The AI provider responded correctly.")
            return self._show_message(
                "Connection warning",
                f"Provider responded but with unexpected content: {(result or '')[:200]}",
            )
        except Exception as exc:
            return self._show_message("Connection failed", str(exc), is_error=True)

    def _show_message(self, title, message, is_error=False):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": "danger" if is_error else "success",
                "sticky": is_error,
            },
        }

    def action_clear_cache(self):
        """Delete all AI response cache entries."""
        count = self.env["security.ai.cache"].search_count([])
        self.env["security.ai.cache"].search([]).unlink()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Cache Cleared",
                "message": f"Deleted {count} cached AI response(s).",
                "type": "success",
            },
        }

    @api.model
    def get_active_config(self):
        config = self.search([("active", "=", True)], limit=1)
        if not config:
            raise UserError(
                "No active AI Engine configuration found. "
                "Go to Configuration → AI Engine to set up your API key."
            )
        return config


class SecurityAILog(models.Model):
    """Immutable audit trail for every AI API call made by the engine."""
    _name = "security.ai.log"
    _description = "Security AI Call Log"
    _order = "call_date desc, id desc"

    config_id = fields.Many2one("security.ai.config", ondelete="set null")
    feature = fields.Char(required=True)
    provider = fields.Char(required=True)
    model_name = fields.Char()
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user.id)
    call_date = fields.Datetime(default=fields.Datetime.now, required=True)
    request_preview = fields.Text(string="Request (preview)")
    response_preview = fields.Text(string="Response (preview)")
    duration_ms = fields.Integer(string="Duration (ms)")
    tokens_in = fields.Integer(string="Input Tokens", default=0)
    tokens_out = fields.Integer(string="Output Tokens", default=0)
    estimated_cost_usd = fields.Float(string="Est. Cost (USD)", digits=(10, 6), default=0.0)
    prompt_version = fields.Char(string="Prompt Version", help="SHA-256 prefix of the system prompt used.")
    cache_hit = fields.Boolean(string="Cache Hit", default=False, help="Response was served from cache (no API call).")
    state = fields.Selection(
        [("success", "Success"), ("error", "Error")],
        required=True,
        default="success",
    )
    error_message = fields.Text()
