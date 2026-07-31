from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SecuritySiteSetupWizard(models.Model):
    _name = "security.site.setup.wizard"
    _description = "Quick Client Site Setup Wizard"

    partner_id = fields.Many2one(
        "res.partner",
        string="Client / Partner",
        required=True,
        domain=[("is_company", "=", True)],
    )
    site_name = fields.Char("Proposed Site Name", required=True, default="Main Facility / Mine Expansion")
    code = fields.Char("Site Code (Optional)", help="Leave blank to auto-generate e.g. SITE-KNS-001")
    site_type = fields.Selection(
        [
            ("mining", "Mining / Heavy Industrial"),
            ("industrial", "Factory / Warehouse"),
            ("commercial", "Commercial Office"),
            ("residential", "Residential Estate"),
            ("retail", "Retail / Mall"),
            ("embassy", "Embassy / High Security"),
            ("banking", "Banking / Financial"),
            ("healthcare", "Healthcare / Hospital"),
        ],
        string="Site Sector",
        default="commercial",
        required=True,
    )
    location = fields.Char("Physical Address / Location")
    supervisor_id = fields.Many2one("hr.employee", string="Site Supervisor", domain=[("security_guard", "=", True)])
    
    # Initial Gate Post Setup
    main_gate_guards = fields.Integer("Main Gate Guards", default=2, required=True)
    patrol_guards = fields.Integer("Patrol Guards", default=1, required=True)
    control_room_guards = fields.Integer("Control Room / CCTV Guards", default=0)
    
    shift_duration = fields.Selection([("12h", "12-Hour Shifts"), ("8h", "8-Hour Shifts")], default="12h", required=True)
    is_24_7 = fields.Boolean("24/7 Continuous Coverage", default=True)

    def action_create_site(self):
        self.ensure_one()
        
        # 1. Code auto-generation if not supplied
        code = self.code
        if not code:
            client_prefix = (self.partner_id.name[:3] if self.partner_id.name else "STE").upper()
            seq = self.env["security.client.site"].search_count([("partner_id", "=", self.partner_id.id)]) + 1
            code = f"SITE-{client_prefix}-{seq:03d}"

        # 2. Create Client Site
        site = self.env["security.client.site"].create({
            "name": self.site_name,
            "code": code,
            "partner_id": self.partner_id.id,
            "site_type": self.site_type,
            "location": self.location,
            "supervisor_id": self.supervisor_id.id if self.supervisor_id else False,
            "active": True,
        })

        # Get or create standard post types
        post_type_model = self.env["security.post.type"]
        gate_pt = post_type_model.search([("name", "ilike", "gate")], limit=1) or post_type_model.search([], limit=1)
        patrol_pt = post_type_model.search([("name", "ilike", "patrol")], limit=1) or gate_pt
        cctv_pt = post_type_model.search([("name", "ilike", "control")], limit=1) or gate_pt

        # Get default shift templates
        shift_model = self.env["security.shift.template"]
        day_shift = shift_model.search([("name", "ilike", "day")], limit=1) or shift_model.search([], limit=1)
        night_shift = shift_model.search([("name", "ilike", "night")], limit=1) or day_shift

        # 3. Create Posts & Shift Requirements
        posts_to_create = []
        if self.main_gate_guards > 0:
            posts_to_create.append(("Main Gate & Access Control", self.main_gate_guards, gate_pt))
        if self.patrol_guards > 0:
            posts_to_create.append(("Perimeter Patrol", self.patrol_guards, patrol_pt))
        if self.control_room_guards > 0:
            posts_to_create.append(("Control Room / CCTV", self.control_room_guards, cctv_pt))

        for post_name, req_guards, pt in posts_to_create:
            post = self.env["security.post"].create({
                "name": f"{site.name} — {post_name}",
                "site_id": site.id,
                "partner_id": self.partner_id.id,
                "post_type_id": pt.id if pt else False,
                "required_guard_count": req_guards,
            })

            # Create Shift Requirements
            if day_shift:
                self.env["security.shift.requirement"].create({
                    "post_id": post.id,
                    "site_id": site.id,
                    "shift_template_id": day_shift.id,
                    "guards_required": req_guards,
                    "active": True,
                })
            if self.is_24_7 and night_shift:
                self.env["security.shift.requirement"].create({
                    "post_id": post.id,
                    "site_id": site.id,
                    "shift_template_id": night_shift.id,
                    "guards_required": req_guards,
                    "active": True,
                })

            # Add default equipment requirements if mining/industrial or high security
            if self.site_type in ["mining", "industrial", "embassy", "banking"]:
                self.env["security.post.resource.requirement"].create({
                    "post_id": post.id,
                    "resource_category": "radio",
                    "name": "Two-Way Radio",
                    "qty_required": 1,
                    "is_mandatory": True,
                })
                self.env["security.post.resource.requirement"].create({
                    "post_id": post.id,
                    "resource_category": "torch",
                    "name": "Heavy Duty Flashlight",
                    "qty_required": 1,
                    "is_mandatory": True,
                })

        return {
            "type": "ir.actions.act_window",
            "name": _("Client Site Form"),
            "res_model": "security.client.site",
            "res_id": site.id,
            "view_mode": "form",
            "target": "current",
        }
