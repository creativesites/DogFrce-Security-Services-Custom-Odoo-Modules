# -*- coding: utf-8 -*-

import datetime
from odoo import api, fields, models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    roster_cycle_start_day = fields.Integer(
        string="Roster Cycle Start Day",
        default=21,
        help="Day of month when the monthly roster cycle starts (e.g. 21 for 21st of previous month).",
    )
    roster_cycle_end_day = fields.Integer(
        string="Roster Cycle End Day",
        default=20,
        help="Day of month when the monthly roster cycle ends (e.g. 20 for 20th of target month).",
    )
    roster_auto_generate_slots = fields.Boolean(
        string="Auto-Generate Slots on Batch Creation",
        default=True,
        help="Automatically generate empty shift slots from site shift requirements when a new batch is created.",
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    roster_cycle_start_day = fields.Integer(
        related="company_id.roster_cycle_start_day",
        readonly=False,
        string="Roster Cycle Start Day",
    )
    roster_cycle_end_day = fields.Integer(
        related="company_id.roster_cycle_end_day",
        readonly=False,
        string="Roster Cycle End Day",
    )
    roster_auto_generate_slots = fields.Boolean(
        related="company_id.roster_auto_generate_slots",
        readonly=False,
        string="Auto-Generate Slots on Batch Creation",
    )

    @api.model
    def get_company_roster_cycle_defaults(self, month=None, year=None):
        """
        Computes prefilled date_from and date_to for a roster cycle based on company settings.
        Default Dogforce cycle: 21st of previous month to 20th of target month.
        """
        company = self.env.company
        start_day = company.roster_cycle_start_day or 21
        end_day = company.roster_cycle_end_day or 20

        # Validate range limits (1-28)
        start_day = max(1, min(28, start_day))
        end_day = max(1, min(28, end_day))

        now = datetime.date.today()
        target_year = int(year) if year else now.year
        target_month = int(month) if month else now.month

        # If start_day > end_day (e.g. 21st to 20th), date_from starts in previous month
        if start_day > end_day:
            if target_month == 1:
                prev_month = 12
                prev_year = target_year - 1
            else:
                prev_month = target_month - 1
                prev_year = target_year

            date_from = datetime.date(prev_year, prev_month, start_day)
            date_to = datetime.date(target_year, target_month, end_day)
        else:
            # Same calendar month cycle (e.g. 1st to 30th/31st)
            date_from = datetime.date(target_year, target_month, start_day)
            # Find last day of target month or end_day
            if end_day >= 28:
                if target_month == 12:
                    next_month_start = datetime.date(target_year + 1, 1, 1)
                else:
                    next_month_start = datetime.date(target_year, target_month + 1, 1)
                last_day = (next_month_start - datetime.timedelta(days=1)).day
                actual_end = min(end_day, last_day)
            else:
                actual_end = end_day
            date_to = datetime.date(target_year, target_month, actual_end)

        return {
            "start_day": start_day,
            "end_day": end_day,
            "auto_generate": company.roster_auto_generate_slots,
            "date_from": date_from.strftime("%Y-%m-%d"),
            "date_to": date_to.strftime("%Y-%m-%d"),
            "target_month": target_month,
            "target_year": target_year,
            "cycle_label": f"{date_from.strftime('%d %b %Y')} – {date_to.strftime('%d %b %Y')}",
        }
