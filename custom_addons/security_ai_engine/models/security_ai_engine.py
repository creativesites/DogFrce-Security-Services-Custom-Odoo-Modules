import hashlib
import time

from odoo import api, models
from odoo.exceptions import UserError

from ..providers import get_provider

_INTERNAL_FEATURES = {"__test__"}

# Cost per 1 000 tokens (input, output) in USD — approximate 2025 rates
_COST_RATES = {
    "claude-opus-4-8":   (0.015,   0.075),
    "claude-opus-4-7":   (0.015,   0.075),
    "claude-sonnet-4-6": (0.003,   0.015),
    "claude-haiku-4-5":  (0.0008,  0.004),
    "gpt-4o":            (0.005,   0.015),
    "gpt-4o-mini":       (0.00015, 0.0006),
    "o1":                (0.015,   0.060),
    "gemini-2.5-flash":  (0.00075, 0.003),
    "gemini-2.0-flash":  (0.0001,  0.0004),
    "gemini-1.5-pro":    (0.00125, 0.005),
}


def _estimate_cost_usd(model_name, tokens_in, tokens_out):
    if not model_name:
        return 0.0
    for key, (rate_in, rate_out) in _COST_RATES.items():
        if key in model_name:
            return round(
                (tokens_in / 1000.0) * rate_in + (tokens_out / 1000.0) * rate_out,
                6,
            )
    return 0.0


def _cache_key(feature, system_prompt, user_message):
    raw = f"{feature}\x00{system_prompt}\x00{user_message}"
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()


def _prompt_version(system_prompt):
    return hashlib.sha256(system_prompt.encode("utf-8", errors="replace")).hexdigest()[:12]


class SecurityAIEngine(models.AbstractModel):
    """
    Provider-agnostic AI facade with caching, multi-provider fallback,
    token tracking, and prompt versioning.

    Usage:
        result = self.env["security.ai.engine"].complete(
            feature="attendance_anomaly",
            system_prompt="...",
            user_message="...",
        )
    Returns None if the feature is disabled or no config is active.
    Returns the response text string on success.
    Raises UserError on auth misconfiguration.
    """
    _name = "security.ai.engine"
    _description = "Security AI Engine Facade"

    _FEATURE_FLAG_MAP = {
        "attendance_anomaly":  "feature_attendance_anomaly",
        "risk_profiling":      "feature_risk_profiling",
        "billing_auditor":     "feature_billing_auditor",
        "roster_optimizer":    "feature_roster_optimizer",
        "shift_fill":          "feature_shift_fill",
        "incident_advisor":    "feature_incident_advisor",
        "leave_coverage":      "feature_leave_coverage",
        "doc_renewal_letter":  "feature_doc_renewal_letter",
        "performance_review":  "feature_performance_review",
        "payslip_explain":     "feature_payslip_explain",
    }

    @api.model
    def complete(self, feature, system_prompt, user_message, config=None, **kwargs):
        # ── Resolve config ────────────────────────────────────────────────────
        if config is None:
            try:
                config = self.env["security.ai.config"].get_active_config()
            except UserError:
                return None

        # ── Feature toggle check ──────────────────────────────────────────────
        if feature not in _INTERNAL_FEATURES:
            flag = self._FEATURE_FLAG_MAP.get(feature)
            if flag and not getattr(config, flag, True):
                return None

        # ── Cache lookup ──────────────────────────────────────────────────────
        ck = _cache_key(feature, system_prompt, user_message)
        if config.enable_response_cache and feature not in _INTERNAL_FEATURES:
            from datetime import timedelta
            from odoo import fields as ofields
            ttl_hours = max(1, config.cache_ttl_hours or 24)
            cutoff = ofields.Datetime.subtract(ofields.Datetime.now(), hours=ttl_hours)
            cached = self.env["security.ai.cache"].sudo().search(
                [("cache_key", "=", ck), ("created_at", ">=", cutoff)],
                limit=1,
            )
            if cached:
                cached.sudo().write({"hit_count": cached.hit_count + 1})
                self.env["security.ai.log"].sudo().create({
                    "config_id": config.id,
                    "feature": feature,
                    "provider": config.active_provider,
                    "model_name": "",
                    "user_id": self.env.uid,
                    "request_preview": (user_message or "")[:500],
                    "response_preview": (cached.response or "")[:500],
                    "duration_ms": 0,
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "estimated_cost_usd": 0.0,
                    "prompt_version": _prompt_version(system_prompt),
                    "cache_hit": True,
                    "state": "success",
                })
                return cached.response

        # ── Resolve provider ──────────────────────────────────────────────────
        provider_key = config.active_provider
        api_key, model_override = self._resolve_provider_settings(config, provider_key)

        if not api_key:
            raise UserError(
                f"No API key configured for {provider_key}. "
                "Go to Configuration → AI Engine to add your key."
            )

        max_tokens = kwargs.get("max_tokens") or config.max_tokens
        temperature = (
            kwargs.get("temperature")
            if kwargs.get("temperature") is not None
            else config.temperature
        )
        model_name = model_override or ""
        pv = _prompt_version(system_prompt)

        provider = get_provider(provider_key, api_key, model_override=model_override or None)

        start_ms = int(time.monotonic() * 1000)
        log_vals = {
            "config_id": config.id,
            "feature": feature,
            "provider": provider_key,
            "model_name": model_name,
            "user_id": self.env.uid,
            "request_preview": (user_message or "")[:500],
            "prompt_version": pv,
            "cache_hit": False,
            "state": "success",
        }

        try:
            result = self._call_provider(provider, system_prompt, user_message, max_tokens, temperature)
            log_vals.update({
                "response_preview": (result.text or "")[:500],
                "tokens_in":  result.tokens_in,
                "tokens_out": result.tokens_out,
                "estimated_cost_usd": _estimate_cost_usd(model_name, result.tokens_in, result.tokens_out),
            })
            text = result.text

        except Exception as primary_exc:
            # ── Multi-provider fallback ───────────────────────────────────────
            fallback = getattr(config, "fallback_provider", "none") or "none"
            if fallback != "none" and fallback != provider_key:
                fb_key, fb_model = self._resolve_provider_settings(config, fallback)
                if fb_key:
                    try:
                        fb_provider = get_provider(fallback, fb_key, model_override=fb_model or None)
                        result = self._call_provider(fb_provider, system_prompt, user_message, max_tokens, temperature)
                        log_vals.update({
                            "provider":   fallback,
                            "model_name": fb_model or "",
                            "response_preview": (result.text or "")[:500],
                            "tokens_in":  result.tokens_in,
                            "tokens_out": result.tokens_out,
                            "estimated_cost_usd": _estimate_cost_usd(fb_model or "", result.tokens_in, result.tokens_out),
                        })
                        text = result.text
                    except Exception as fb_exc:
                        log_vals["state"] = "error"
                        log_vals["error_message"] = f"Primary: {primary_exc} | Fallback: {fb_exc}"[:1000]
                        log_vals.setdefault("duration_ms", int(time.monotonic() * 1000) - start_ms)
                        self.env["security.ai.log"].sudo().create(log_vals)
                        return None
                else:
                    log_vals["state"] = "error"
                    log_vals["error_message"] = str(primary_exc)[:1000]
                    log_vals.setdefault("duration_ms", int(time.monotonic() * 1000) - start_ms)
                    self.env["security.ai.log"].sudo().create(log_vals)
                    if "API key" in str(primary_exc) or "401" in str(primary_exc) or "403" in str(primary_exc):
                        raise UserError(f"AI auth failed: {primary_exc}") from primary_exc
                    return None
            else:
                log_vals["state"] = "error"
                log_vals["error_message"] = str(primary_exc)[:1000]
                log_vals.setdefault("duration_ms", int(time.monotonic() * 1000) - start_ms)
                self.env["security.ai.log"].sudo().create(log_vals)
                if "API key" in str(primary_exc) or "401" in str(primary_exc) or "403" in str(primary_exc):
                    raise UserError(f"AI auth failed: {primary_exc}") from primary_exc
                return None

        finally:
            log_vals.setdefault("duration_ms", int(time.monotonic() * 1000) - start_ms)

        # ── Write log + store in cache ────────────────────────────────────────
        self.env["security.ai.log"].sudo().create(log_vals)

        if config.enable_response_cache and feature not in _INTERNAL_FEATURES and text:
            try:
                self.env["security.ai.cache"].sudo().create({
                    "cache_key": ck,
                    "feature": feature,
                    "response": text,
                })
            except Exception:
                pass  # Unique constraint violation = already cached by concurrent call

        return text

    @staticmethod
    def _call_provider(provider, system_prompt, user_message, max_tokens, temperature):
        return provider.complete(
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    @staticmethod
    def _resolve_provider_settings(config, provider_key):
        if provider_key == "claude":
            return config.claude_api_key, config.claude_model
        if provider_key == "openai":
            return config.openai_api_key, config.openai_model
        if provider_key == "gemini":
            return config.gemini_api_key, config.gemini_model
        return None, None
