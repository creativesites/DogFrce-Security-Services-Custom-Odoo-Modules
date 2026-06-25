import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Set Namibia as the default company localization on first install."""
    namibia = env.ref("base.na", raise_if_not_found=False)
    if not namibia:
        _logger.warning(
            "DogForce: Namibia country record (base.na) not found — "
            "localization defaults skipped."
        )
        return

    nad = env["res.currency"].search([("name", "=", "NAD")], limit=1)

    for company in env["res.company"].search([]):
        vals = {}
        if not company.country_id:
            vals["country_id"] = namibia.id
        if nad and company.currency_id != nad:
            try:
                vals["currency_id"] = nad.id
            except Exception:
                pass
        if vals:
            company.sudo().write(vals)

    _logger.info("DogForce: Namibia localization defaults applied.")

    # Warn if multiple l10n modules are active (only one should be).
    l10n_modules = env["ir.module.module"].search([
        ("name", "=like", "l10n_%"),
        ("state", "=", "installed"),
    ])
    if len(l10n_modules) > 1:
        names = ", ".join(l10n_modules.mapped("name"))
        _logger.warning(
            "DogForce: Multiple localization modules are active: %s. "
            "Only one country localization should be active at a time.",
            names,
        )
