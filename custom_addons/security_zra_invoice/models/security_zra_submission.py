import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SecurityZraSubmission(models.Model):
    _name = "security.zra.submission"
    _description = "ZRA Smart Invoice Submission"
    _order = "create_date desc"
    _rec_name = "display_name"

    display_name = fields.Char(compute="_compute_display_name", store=True)

    # Links — exactly one of these is set per record.
    invoice_id = fields.Many2one(
        "security.billing.invoice",
        ondelete="cascade",
        index=True,
        string="Invoice",
    )
    credit_note_id = fields.Many2one(
        "security.billing.credit.note",
        ondelete="cascade",
        index=True,
        string="Credit Note",
    )
    submission_type = fields.Selection(
        [("invoice", "Invoice"), ("credit_note", "Credit Note")],
        required=True,
        default="invoice",
    )

    # Lifecycle state
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
            ("error", "Error"),
        ],
        required=True,
        default="pending",
    )

    # ZRA response data
    zra_internal_data = fields.Char(string="Internal Data (QR Hash)")
    zra_receipt_no = fields.Char(string="Receipt Number")
    zra_signature = fields.Char(string="Signature")
    zra_sdc_id = fields.Char(string="SDC ID")
    zra_mrc_no = fields.Char(string="MRC Number")
    zra_vsdc_date = fields.Char(string="VSDC Receipt Date")

    # Audit trail
    raw_request = fields.Text(string="Request Payload")
    raw_response = fields.Text(string="Response Payload")
    error_message = fields.Text(string="Error")
    retry_count = fields.Integer(default=0, string="Retry Count")
    last_attempt = fields.Datetime(string="Last Attempt")
    accepted_at = fields.Datetime(string="Accepted At")

    @api.depends("invoice_id.name", "credit_note_id.name", "submission_type")
    def _compute_display_name(self):
        for rec in self:
            ref = rec.invoice_id.name or rec.credit_note_id.name or "—"
            label = "INV" if rec.submission_type == "invoice" else "CN"
            rec.display_name = f"ZRA/{label}/{ref}"

    @api.model
    def action_retry_pending(self):
        """Cron entry-point: retry pending/errored submissions with exponential backoff.

        Backoff schedule (minutes to wait after the previous attempt):
          retry 1 → wait  2 min
          retry 2 → wait 10 min
          retry 3 → wait 30 min
          retry 4 → wait 120 min (2 hr)
          retry 5 → wait 240 min (4 hr)
        After 5 retries the cron stops touching the record; staff must intervene.
        """
        BACKOFF_MINUTES = {1: 2, 2: 10, 3: 30, 4: 120, 5: 240}

        pending = self.search([
            ("state", "in", ("pending", "error")),
            ("retry_count", "<", 5),
        ])
        now = fields.Datetime.now()
        for sub in pending:
            if sub.last_attempt:
                wait_minutes = BACKOFF_MINUTES.get(sub.retry_count, 2)
                elapsed_minutes = (now - sub.last_attempt).total_seconds() / 60.0
                if elapsed_minutes < wait_minutes:
                    continue
            try:
                if sub.invoice_id:
                    sub.invoice_id._submit_to_zra(existing_submission=sub)
                elif sub.credit_note_id:
                    sub.credit_note_id._submit_credit_note_to_zra(existing_submission=sub)
            except Exception as exc:
                _logger.error(
                    "ZRA retry failed for submission %s (%s): %s",
                    sub.id, sub.display_name, exc,
                )
