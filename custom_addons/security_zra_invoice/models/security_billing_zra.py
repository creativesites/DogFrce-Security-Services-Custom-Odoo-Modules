import json
import logging
from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# ZRA item classification code for security & investigation services
_SECURITY_ITEM_CLASS = "S019"


def _build_item_list(lines, vat_rate):
    """Convert billing invoice lines to ZRA itemList entries."""
    vat_category = "B" if vat_rate > 0 else "A"
    items = []
    for idx, line in enumerate(lines, start=1):
        subtotal = line.subtotal
        tax_amt = round(subtotal * (vat_rate / 100.0), 2) if vat_rate else 0.0
        tot_amt = round(subtotal + tax_amt, 2)
        items.append({
            "itemSeq": idx,
            "itemCd": f"SRV{idx:03d}",
            "itemClsCd": _SECURITY_ITEM_CLASS,
            "itemNm": (line.name or "Security Service")[:100],
            "pkgUnt": "",
            "pkg": 0,
            "qtyUnt": "EA",
            "qty": line.quantity,
            "prc": round(line.unit_price, 2),
            "splyAmt": round(subtotal, 2),
            "dcRt": 0.0,
            "dcAmt": 0.0,
            "isrccCd": "",
            "isrccNm": "",
            "isrcRt": 0.0,
            "isrcAmt": 0.0,
            "vatCatCd": vat_category,
            "exciseTxCatCd": "",
            "vatTaxblAmt": round(subtotal, 2) if vat_category == "B" else 0.0,
            "exciseTxblAmt": 0.0,
            "exciseTxAmt": 0.0,
            "vatAmt": tax_amt,
            "totAmt": tot_amt,
        })
    return items


def _tax_block(subtotal_amount, vat_amount, vat_rate):
    """Build the repeated tax category fields expected by the VSDC API."""
    vat_cat = "B" if vat_rate > 0 else "A"
    return {
        "taxblAmtA": 0.0 if vat_cat == "B" else round(subtotal_amount, 2),
        "taxblAmtB": round(subtotal_amount, 2) if vat_cat == "B" else 0.0,
        "taxblAmtC1": 0.0, "taxblAmtC2": 0.0, "taxblAmtC3": 0.0,
        "taxblAmtD": 0.0, "taxblAmtRvat": 0.0, "taxblAmtE": 0.0, "taxblAmtF": 0.0,
        "taxRtA": 0.0,
        "taxRtB": float(vat_rate) if vat_cat == "B" else 0.0,
        "taxRtC1": 0.0, "taxRtC2": 0.0, "taxRtC3": 0.0,
        "taxRtD": 0.0, "taxRtRvat": 0.0, "taxRtE": 0.0, "taxRtF": 0.0,
        "taxAmtA": 0.0,
        "taxAmtB": round(vat_amount, 2) if vat_cat == "B" else 0.0,
        "taxAmtC1": 0.0, "taxAmtC2": 0.0, "taxAmtC3": 0.0,
        "taxAmtD": 0.0, "taxAmtRvat": 0.0, "taxAmtE": 0.0, "taxAmtF": 0.0,
        "totTaxblAmt": round(subtotal_amount, 2),
        "totTaxAmt": round(vat_amount, 2),
    }


def _store_zra_response(sub, raw_req, raw_resp, zra_data, now):
    sub.write({
        "state": "accepted",
        "raw_request": raw_req,
        "raw_response": raw_resp,
        "zra_internal_data": zra_data.get("intrlData", ""),
        "zra_receipt_no": str(zra_data.get("rcptNo", "")),
        "zra_signature": zra_data.get("rcptSign", ""),
        "zra_sdc_id": zra_data.get("sdcId", ""),
        "zra_mrc_no": zra_data.get("mrcNo", ""),
        "zra_vsdc_date": zra_data.get("vsdcRcptPbctDate", ""),
        "accepted_at": now,
        "error_message": False,
    })


class SecurityBillingInvoiceZra(models.Model):
    _inherit = "security.billing.invoice"

    zra_submission_ids = fields.One2many(
        "security.zra.submission",
        "invoice_id",
        string="ZRA Submissions",
    )
    zra_state = fields.Selection(
        [
            ("not_submitted", "Not Submitted"),
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
            ("error", "Error"),
        ],
        compute="_compute_zra_state",
        store=True,
        string="ZRA Status",
    )
    zra_receipt_no = fields.Char(
        compute="_compute_zra_latest",
        store=True,
        string="ZRA Receipt No.",
    )
    zra_internal_data = fields.Char(
        compute="_compute_zra_latest",
        store=True,
        string="ZRA Internal Data",
    )
    zra_qr_code = fields.Binary(
        compute="_compute_zra_qr_code",
        string="ZRA QR Code",
    )

    @api.depends("zra_submission_ids.state", "zra_submission_ids.create_date")
    def _compute_zra_state(self):
        for inv in self:
            latest = inv.zra_submission_ids[:1]
            inv.zra_state = latest.state if latest else "not_submitted"

    @api.depends("zra_submission_ids.zra_receipt_no", "zra_submission_ids.zra_internal_data",
                 "zra_submission_ids.state")
    def _compute_zra_latest(self):
        for inv in self:
            accepted = inv.zra_submission_ids.filtered(lambda s: s.state == "accepted")[:1]
            latest = accepted or inv.zra_submission_ids[:1]
            inv.zra_receipt_no = latest.zra_receipt_no if latest else False
            inv.zra_internal_data = latest.zra_internal_data if latest else False

    @api.depends("zra_internal_data")
    def _compute_zra_qr_code(self):
        for inv in self:
            if not inv.zra_internal_data:
                inv.zra_qr_code = False
                continue
            try:
                import io
                import base64
                import qrcode
                qr = qrcode.QRCode(version=1, box_size=4, border=2)
                qr.add_data(inv.zra_internal_data)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                inv.zra_qr_code = base64.b64encode(buf.getvalue())
            except Exception as exc:
                _logger.warning(
                    "ZRA QR code generation failed for invoice %s: %s", inv.name, exc
                )
                inv.zra_qr_code = False

    def _build_zra_invoice_payload(self):
        self.ensure_one()
        now = datetime.now()
        invoice_dt = (
            datetime.combine(self.invoice_date, datetime.min.time())
            if self.invoice_date else now
        )
        vat_rate = self.vat_rate or 0.0
        items = _build_item_list(self.line_ids, vat_rate)
        payload = {
            "invcNo": self.name,
            "orgInvcNo": "",
            "cisInvcNo": self.name,
            "traderSystemInvcNo": self.name,
            "custNm": (self.partner_id.name or "")[:100],
            "custTpin": self.partner_id.vat or "",
            "custAddr": " ".join(filter(None, [
                self.partner_id.street or "",
                self.partner_id.city or "",
                self.partner_id.country_id.name if self.partner_id.country_id else "",
            ]))[:200],
            "salesTyCd": "N",
            "rcptTyCd": "S",
            "pmtTyCd": "02",
            "salesStsCd": "02",
            "cfmDt": now.strftime("%Y%m%d%H%M%S"),
            "salesDt": invoice_dt.strftime("%Y%m%d"),
            "stockRlsDt": now.strftime("%Y%m%d%H%M%S"),
            "cnclReqDt": "",
            "cnclDt": "",
            "rfdDt": "",
            "rfdRsnCd": "",
            "totItemCnt": len(items),
            **_tax_block(self.subtotal_amount, self.vat_amount, vat_rate),
            "totAmt": round(self.total_amount, 2),
            "prchrAcptcYn": "N",
            "remark": (self.note or "")[:100],
            "regrNm": self.env.user.name,
            "regrId": self.env.user.login,
            "modrNm": self.env.user.name,
            "modrId": self.env.user.login,
            "itemList": items,
        }
        return payload

    def _submit_to_zra(self, existing_submission=None):
        """Core submission logic. Creates or updates a ZRA submission record."""
        self.ensure_one()
        config = self.env["security.zra.config"].get_active_config(
            company_id=self.env.company.id
        )
        if not config:
            raise UserError(
                "No active ZRA configuration found for this company. "
                "Go to Settings → ZRA Smart Invoice to configure."
            )
        from .security_zra_client import ZRAApiError
        client = config._get_client()
        payload = self._build_zra_invoice_payload()
        now = fields.Datetime.now()

        sub = existing_submission or self.env["security.zra.submission"].create({
            "invoice_id": self.id,
            "submission_type": "invoice",
            "state": "pending",
        })
        sub.write({
            "last_attempt": now,
            "retry_count": (sub.retry_count or 0) + (1 if existing_submission else 0),
            "error_message": False,
        })
        try:
            raw_req, raw_resp, data = client.save_sales(payload)
            _store_zra_response(sub, raw_req, raw_resp, data.get("data", {}), now)
        except ZRAApiError as exc:
            sub.write({
                "state": "error",
                "raw_request": json.dumps(payload),
                "error_message": str(exc),
            })
            raise UserError(f"ZRA submission failed: {exc}") from exc
        return sub

    def action_submit_to_zra(self):
        for inv in self:
            if not inv.line_ids:
                raise UserError(
                    f"Invoice {inv.name} has no lines. Add at least one line before submitting."
                )
            inv._submit_to_zra()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "ZRA Submitted",
                "message": "Invoice accepted by ZRA Smart Invoice system.",
                "type": "success",
                "sticky": False,
            },
        }

    def action_view_zra_submissions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"ZRA Submissions — {self.name}",
            "res_model": "security.zra.submission",
            "view_mode": "list,form",
            "domain": [("invoice_id", "=", self.id)],
            "context": {"default_invoice_id": self.id},
        }


class SecurityBillingCreditNoteZra(models.Model):
    _inherit = "security.billing.credit.note"

    zra_submission_ids = fields.One2many(
        "security.zra.submission",
        "credit_note_id",
        string="ZRA Submissions",
    )
    zra_state = fields.Selection(
        [
            ("not_submitted", "Not Submitted"),
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
            ("error", "Error"),
        ],
        compute="_compute_zra_cn_state",
        store=True,
        string="ZRA Status",
    )

    @api.depends("zra_submission_ids.state")
    def _compute_zra_cn_state(self):
        for cn in self:
            latest = cn.zra_submission_ids[:1]
            cn.zra_state = latest.state if latest else "not_submitted"

    def _submit_credit_note_to_zra(self, existing_submission=None):
        self.ensure_one()
        config = self.env["security.zra.config"].get_active_config(
            company_id=self.env.company.id
        )
        if not config:
            raise UserError("No active ZRA configuration found for this company.")
        from .security_zra_client import ZRAApiError
        client = config._get_client()

        orig = self.invoice_id
        orig_receipt = orig.zra_receipt_no if orig else ""
        vat_rate = (orig.vat_rate or 0.0) if orig else 0.0
        vat_category = "B" if vat_rate > 0 else "A"
        tax_amt = round(self.amount * (vat_rate / 100.0), 2)
        tot_amt = round(self.amount + tax_amt, 2)
        now_dt = datetime.now()

        payload = {
            "invcNo": self.name,
            "orgInvcNo": orig_receipt,
            "cisInvcNo": self.name,
            "traderSystemInvcNo": self.name,
            "custNm": (self.partner_id.name or "")[:100] if self.partner_id else "",
            "custTpin": (self.partner_id.vat or "") if self.partner_id else "",
            "custAddr": "",
            "salesTyCd": "N",
            "rcptTyCd": "C",
            "pmtTyCd": "02",
            "salesStsCd": "02",
            "cfmDt": now_dt.strftime("%Y%m%d%H%M%S"),
            "salesDt": now_dt.strftime("%Y%m%d"),
            "stockRlsDt": now_dt.strftime("%Y%m%d%H%M%S"),
            "cnclReqDt": "",
            "cnclDt": "",
            "rfdDt": now_dt.strftime("%Y%m%d"),
            "rfdRsnCd": "01",
            "totItemCnt": 1,
            **_tax_block(self.amount, tax_amt, vat_rate),
            "totAmt": tot_amt,
            "prchrAcptcYn": "N",
            "remark": (self.reason or "")[:100],
            "regrNm": self.env.user.name,
            "regrId": self.env.user.login,
            "modrNm": self.env.user.name,
            "modrId": self.env.user.login,
            "itemList": [{
                "itemSeq": 1,
                "itemCd": "SRV001",
                "itemClsCd": _SECURITY_ITEM_CLASS,
                "itemNm": (f"Credit Note: {orig.name}" if orig else "Credit Note")[:100],
                "pkgUnt": "", "pkg": 0, "qtyUnt": "EA",
                "qty": 1.0,
                "prc": round(self.amount, 2),
                "splyAmt": round(self.amount, 2),
                "dcRt": 0.0, "dcAmt": 0.0,
                "isrccCd": "", "isrccNm": "", "isrcRt": 0.0, "isrcAmt": 0.0,
                "vatCatCd": vat_category,
                "exciseTxCatCd": "",
                "vatTaxblAmt": round(self.amount, 2) if vat_category == "B" else 0.0,
                "exciseTxblAmt": 0.0, "exciseTxAmt": 0.0,
                "vatAmt": tax_amt,
                "totAmt": tot_amt,
            }],
        }

        now = fields.Datetime.now()
        sub = existing_submission or self.env["security.zra.submission"].create({
            "credit_note_id": self.id,
            "submission_type": "credit_note",
            "state": "pending",
        })
        sub.write({
            "last_attempt": now,
            "retry_count": (sub.retry_count or 0) + (1 if existing_submission else 0),
            "error_message": False,
        })
        try:
            raw_req, raw_resp, data = client.save_sales(payload)
            _store_zra_response(sub, raw_req, raw_resp, data.get("data", {}), now)
        except ZRAApiError as exc:
            sub.write({
                "state": "error",
                "raw_request": json.dumps(payload),
                "error_message": str(exc),
            })
            raise UserError(f"ZRA credit note submission failed: {exc}") from exc
        return sub

    def action_submit_credit_note_to_zra(self):
        for cn in self:
            cn._submit_credit_note_to_zra()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "ZRA Submitted",
                "message": "Credit note accepted by ZRA Smart Invoice system.",
                "type": "success",
                "sticky": False,
            },
        }
