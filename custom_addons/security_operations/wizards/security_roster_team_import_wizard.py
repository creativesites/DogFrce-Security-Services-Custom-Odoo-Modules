# -*- coding: utf-8 -*-
import base64
import csv
import io
import re
import difflib
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SecurityRosterTeamImportWizard(models.TransientModel):
    _name = "security.roster.team.import.wizard"
    _description = "Import Regular Site Guards from Roster Documents"

    site_id = fields.Many2one(
        "security.client.site",
        string="Client Site",
        required=True,
    )
    file_data = fields.Binary(
        string="Roster Document (Excel / CSV / Text / PDF)",
        required=True,
    )
    file_name = fields.Char(string="File Name")
    source_label = fields.Char(
        string="Source Roster Label",
        required=True,
        default="DogForce Manual Roster",
        help="E.g. DogForce October 2026 Paper Roster, Excel Schedule Sheet",
    )
    guard_pool_mode = fields.Selection(
        [
            ("site_only", "Regular Site Pool Only"),
            ("site_then_relief", "Site Pool with Relief Fallback"),
        ],
        string="Guard Pool Mode",
        default="site_only",
        required=True,
    )
    state = fields.Selection(
        [
            ("upload", "Upload Document"),
            ("review", "Review & Match Guards"),
            ("done", "Completed"),
        ],
        default="upload",
        required=True,
    )
    line_ids = fields.One2many(
        "security.roster.team.import.wizard.line",
        "wizard_id",
        string="Extracted Guards",
    )
    matched_count = fields.Integer(
        string="Matched Guards",
        compute="_compute_counts",
    )
    unmatched_count = fields.Integer(
        string="Unmatched Guards",
        compute="_compute_counts",
    )
    total_guards_found = fields.Integer(
        string="Total Candidates Found",
        compute="_compute_counts",
    )

    @api.depends("line_ids", "line_ids.match_status", "line_ids.employee_id")
    def _compute_counts(self):
        for wiz in self:
            wiz.total_guards_found = len(wiz.line_ids)
            wiz.matched_count = len(wiz.line_ids.filtered(lambda l: l.employee_id and l.match_status in ("exact", "fuzzy", "manual")))
            wiz.unmatched_count = len(wiz.line_ids.filtered(lambda l: not l.employee_id or l.match_status == "unmatched"))

    def action_parse_document(self):
        """Parse uploaded document, extract candidate names, and match against hr.employee."""
        self.ensure_one()
        if not self.file_data:
            raise UserError(_("Please upload a roster document to proceed."))

        try:
            file_bytes = base64.b64decode(self.file_data)
        except Exception as e:
            raise UserError(_("Could not decode uploaded file: %s") % str(e))

        filename = (self.file_name or "").lower()
        extracted_names = []

        if filename.endswith(".csv"):
            extracted_names = self._parse_csv(file_bytes)
        elif filename.endswith(".xlsx") or filename.endswith(".xlsm") or filename.endswith(".xltx"):
            extracted_names = self._parse_xlsx(file_bytes)
        else:
            # Fallback text / general text parsing
            extracted_names = self._parse_text_content(file_bytes)

        if not extracted_names:
            raise UserError(_(
                "No guard names could be detected in the uploaded file. "
                "Please verify the file format or ensure it contains guard names or ID numbers."
            ))

        # Clear existing lines
        self.line_ids.unlink()

        # Query all active security guards for matching
        guards = self.env["hr.employee"].search([
            ("security_guard", "=", True),
            ("active", "=", True),
        ])

        new_lines = []
        for raw_name in extracted_names:
            clean_name = raw_name.strip()
            if not clean_name or len(clean_name) < 2:
                continue

            matched_emp, status, confidence, note = self._match_employee(clean_name, guards)
            new_lines.append({
                "wizard_id": self.id,
                "raw_guard_name": clean_name,
                "employee_id": matched_emp.id if matched_emp else False,
                "match_status": status,
                "confidence_pct": confidence,
                "include_in_pool": bool(matched_emp),
                "note": note,
            })

        self.env["security.roster.team.import.wizard.line"].create(new_lines)
        self.state = "review"
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _parse_csv(self, file_bytes):
        names = []
        for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                text = file_bytes.decode(encoding)
                reader = csv.reader(io.StringIO(text))
                for row in reader:
                    for cell in row:
                        val = self._clean_token(cell)
                        if val and val not in names:
                            names.append(val)
                break
            except Exception:
                continue
        return names

    def _parse_xlsx(self, file_bytes):
        names = []
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True, read_only=True)
            for sheet in wb.worksheets:
                for row in sheet.iter_rows(values_only=True):
                    for cell in row:
                        if cell is not None:
                            val = self._clean_token(str(cell))
                            if val and val not in names:
                                names.append(val)
        except Exception as e:
            _logger.warning("openpyxl parsing failed: %s, falling back to text parsing", e)
            return self._parse_text_content(file_bytes)
        return names

    def _parse_text_content(self, file_bytes):
        names = []
        text = ""
        for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                text = file_bytes.decode(encoding)
                break
            except Exception:
                continue

        if not text:
            text = str(file_bytes)

        lines = text.splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Tokenize line or extract name-like patterns
            tokens = re.split(r"[,\t;|]", line)
            for tok in tokens:
                clean_tok = self._clean_token(tok)
                if clean_tok and clean_tok not in names:
                    names.append(clean_tok)
        return names

    def _clean_token(self, token):
        if not token:
            return False
        clean = str(token).strip()
        # Remove quotation marks
        clean = re.sub(r"^[\"']|[\"']$", "", clean).strip()

        # Ignore common non-guard strings
        ignored = {
            "day", "night", "off", "shift", "shifts", "site", "client", "total", "hours",
            "name", "guard", "guard name", "date", "rank", "grade", "post", "mon", "tue",
            "wed", "thu", "fri", "sat", "sun", "monday", "tuesday", "wednesday", "thursday",
            "friday", "saturday", "sunday", "status", "present", "absent", "leave", "time",
            "sign", "signature", "remarks", "location", "notes", "contact", "phone", "yes", "no"
        }
        if clean.lower() in ignored:
            return False
        # Ignore pure numbers or pure dates
        if re.match(r"^\d+(\.\d+)?$", clean) or re.match(r"^\d{4}-\d{2}-\d{2}$", clean) or re.match(r"^\d{2}/\d{2}/\d{4}$", clean):
            return False
        # Must have at least some alphabetic characters
        if not re.search(r"[a-zA-Z]", clean):
            return False
        # Avoid huge sentences
        if len(clean) > 50 or len(clean) < 2:
            return False

        # Remove prefix titles if present
        clean = re.sub(r"^(guard|officer|mr|ms|mrs|s/o)\.?\s+", "", clean, flags=re.IGNORECASE)
        return clean.strip()

    def _match_employee(self, raw_name, guards):
        """Match candidate name against active security guards using 4-tier comparison."""
        raw_norm = self._normalize_name(raw_name)

        # 1. Exact match on Guard ID / Employee Code
        for g in guards:
            if g.employee_code and g.employee_code.strip().lower() == raw_name.strip().lower():
                return g, "exact", 100, f"Matched via Guard ID ({g.employee_code})"

        # 2. Exact match on full name
        for g in guards:
            if self._normalize_name(g.name) == raw_norm:
                return g, "exact", 100, "Exact full name match"

        # 3. Transposed / inverted name match (e.g. 'Phiri, Peter' vs 'Peter Phiri')
        raw_tokens = set(raw_norm.split())
        for g in guards:
            g_tokens = set(self._normalize_name(g.name).split())
            if raw_tokens and raw_tokens == g_tokens:
                return g, "exact", 95, "Matched all name parts (transposed)"

        # 4. Fuzzy SequenceMatcher ratio
        best_guard = None
        best_ratio = 0.0
        for g in guards:
            g_norm = self._normalize_name(g.name)
            ratio = difflib.SequenceMatcher(None, raw_norm, g_norm).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_guard = g

        if best_guard and best_ratio >= 0.82:
            return best_guard, "fuzzy", int(best_ratio * 100), f"Suggested match ({int(best_ratio * 100)}% similarity to '{best_guard.name}')"

        return False, "unmatched", 0, "Unmatched guard — requires HR/manager review"

    def _normalize_name(self, text):
        if not text:
            return ""
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        return " ".join(text.split())

    def action_confirm_import(self):
        """Commit confirmed matched guards into site's regular pool."""
        self.ensure_one()
        confirmed_lines = self.line_ids.filtered(lambda l: l.include_in_pool and l.employee_id)
        if not confirmed_lines:
            raise UserError(_("No guards were selected to be added to the site pool."))

        confirmed_guards = confirmed_lines.mapped("employee_id")
        self.site_id.site_guard_pool_ids = [(6, 0, confirmed_guards.ids)]
        self.site_id.guard_pool_mode = self.guard_pool_mode
        self.site_id.guard_pool_source = self.source_label
        self.site_id.guard_pool_source_date = fields.Date.today()

        unmatched_lines = self.line_ids.filtered(lambda l: not l.employee_id)
        unmatched_names = ", ".join(unmatched_lines.mapped("raw_guard_name")) if unmatched_lines else "None"

        # Audit chatter message
        guard_names_list = ", ".join(confirmed_guards.mapped("name"))
        if hasattr(self.site_id, "message_post"):
            self.site_id.message_post(
                body=f"<b>Regular Site Guards Configured via Document Import</b><br/>"
                     f"<b>Source:</b> {self.source_label} ({self.file_name or 'Uploaded Document'})<br/>"
                     f"<b>Confirmed Guards ({len(confirmed_guards)}):</b> {guard_names_list}<br/>"
                     f"<b>Guard Pool Mode:</b> {self.guard_pool_mode}<br/>"
                     f"<b>Unmatched / Skipped Names:</b> {unmatched_names}",
                message_type="notification",
            )

        self.state = "done"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Import Successful"),
                "message": _("%d regular guards configured for site '%s'.") % (len(confirmed_guards), self.site_id.name),
                "type": "success",
                "sticky": False,
            }
        }


class SecurityRosterTeamImportWizardLine(models.TransientModel):
    _name = "security.roster.team.import.wizard.line"
    _description = "Roster Document Extracted Guard Line"
    _order = "match_status desc, confidence_pct desc, id asc"

    wizard_id = fields.Many2one(
        "security.roster.team.import.wizard",
        required=True,
        ondelete="cascade",
    )
    raw_guard_name = fields.Char(string="Name in Document", required=True)
    employee_id = fields.Many2one(
        "hr.employee",
        string="Matched Guard (HR Employee)",
        domain=[("security_guard", "=", True), ("active", "=", True)],
    )
    match_status = fields.Selection(
        [
            ("exact", "Exact Match (100%)"),
            ("fuzzy", "Suggested Match"),
            ("manual", "Manually Selected"),
            ("unmatched", "Unmatched (Requires Review)"),
        ],
        string="Match Status",
        default="unmatched",
        required=True,
    )
    confidence_pct = fields.Integer(string="Confidence (%)", default=0)
    include_in_pool = fields.Boolean(
        string="Include in Team",
        default=True,
    )
    note = fields.Char(string="Notes / Resolution")

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        for line in self:
            if line.employee_id:
                if line.match_status == "unmatched":
                    line.match_status = "manual"
                    line.confidence_pct = 100
                    line.note = "Manually matched by manager"
                line.include_in_pool = True
            else:
                line.match_status = "unmatched"
                line.confidence_pct = 0
                line.include_in_pool = False
                line.note = "Unmatched guard — requires HR/manager review"
