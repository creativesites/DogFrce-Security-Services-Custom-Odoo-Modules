import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

# The Zambia build runs on ZMW; never force another currency onto it.
ZAMBIA_MODULES = ("security_l10n_zm", "security_zra_invoice", "security_demo_data_zm", "security_demo_zambia_site")
PARAM = "dogforce.single_currency"  # currency code; "off" disables


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def _dg_enforce_single_currency(self):
        """Keep every DogForce record in one currency (NAD by default).

        DogForce bills, pays and reports only in Namibian dollars, but records
        such as billing plans, invoices, contracts, loans and payroll rule sets
        each store their own currency, and some were saved in USD. This:

        1. moves every stored currency field defined by a security_* module
           to the target currency (a relabel: the amounts were always
           entered in Namibian dollars);
        2. archives every other currency not used by a company or by posted
           accounting, so it can't be picked again.

        Idempotent; runs from a scheduled action so records added later are
        caught too. Odoo's own accounting entries are never touched.
        """
        ICP = self.env["ir.config_parameter"].sudo()
        code = (ICP.get_param(PARAM) or "NAD").strip().upper()
        if code in ("", "OFF", "0", "FALSE", "NONE"):
            return {"skipped": "disabled"}
        if self.env["ir.module.module"].sudo().search_count(
            [("name", "in", ZAMBIA_MODULES), ("state", "=", "installed")]
        ):
            return {"skipped": "zambia build"}
        Currency = self.env["res.currency"].sudo().with_context(active_test=False)
        target = Currency.search([("name", "=", code)], limit=1)
        if not target:
            _logger.warning("DogForce single currency: %s not found", code)
            return {"skipped": "currency not found"}
        if not target.active:
            target.active = True

        for company in self.sudo().search([]):
            if company.currency_id != target:
                _logger.warning(
                    "DogForce single currency: company %s uses %s, not %s. Change it in "
                    "Settings > Companies if accounting allows.", company.name, company.currency_id.name, code,
                )

        moved = {}
        cr = self.env.cr
        for model_name in list(self.env.registry.models):
            Model = self.env[model_name]
            if Model._abstract or not Model._auto or Model._transient:
                continue
            for fname, field in Model._fields.items():
                if (
                    field.type == "many2one"
                    and field.comodel_name == "res.currency"
                    and field.store
                    and not field.company_dependent
                    and (getattr(field, "_module", None) or "").startswith("security_")
                ):
                    cr.execute(
                        'UPDATE "%s" SET "%s" = %%s WHERE "%s" IS DISTINCT FROM %%s' % (Model._table, fname, fname),
                        (target.id, target.id),
                    )
                    if cr.rowcount:
                        moved["%s.%s" % (model_name, fname)] = cr.rowcount
                        Model.invalidate_model([fname])
        if moved:
            _logger.info("DogForce single currency: moved to %s: %s", code, moved)

        in_use = set(self.sudo().search([]).mapped("currency_id").ids) | {target.id}
        if "account.move.line" in self.env:
            cr.execute("SELECT DISTINCT currency_id FROM account_move_line WHERE currency_id IS NOT NULL")
            in_use |= {row[0] for row in cr.fetchall()}
        others = Currency.search([("active", "=", True), ("id", "not in", list(in_use))])
        archived = others.mapped("name")
        if others:
            try:
                with cr.savepoint():
                    others.write({"active": False})
            except Exception as exc:  # never block the rest of the job
                _logger.warning("DogForce single currency: couldn't archive %s: %s", archived, exc)
                archived = []
        kept = Currency.search([("active", "=", True), ("id", "!=", target.id)]).mapped("name")
        return {"currency": code, "moved": moved, "archived": archived, "still_active": kept}
