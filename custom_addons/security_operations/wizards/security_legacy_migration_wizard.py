from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SecurityLegacyContractMigrationWizard(models.TransientModel):
    _name = "security.legacy.contract.migration.wizard"
    _description = "Legacy Contract & Site Migration Wizard"

    name = fields.Char(default="Legacy Contract Structure Migration", required=True)
    state = fields.Selection([("draft", "Draft"), ("done", "Done")], default="draft")
    contracts_processed = fields.Integer(default=0, readonly=True)
    sites_mapped = fields.Integer(default=0, readonly=True)
    posts_mapped = fields.Integer(default=0, readonly=True)
    requirements_mapped = fields.Integer(default=0, readonly=True)
    needs_review = fields.Integer(default=0, readonly=True)
    report_text = fields.Text(string="Migration Report", readonly=True)

    def action_run_migration(self):
        """
        One-time migration: Converts existing site/post/shift configuration into the contract-first representation.
        Preserves all IDs and historical operational records.
        """
        self.ensure_one()

        contract_model = self.env["security.client.contract"]
        c_site_model = self.env["security.contract.site"]
        c_post_model = self.env["security.contract.post"]
        c_req_model = self.env["security.contract.shift.requirement"]

        contracts = contract_model.search([])
        p_count = 0
        s_count = 0
        post_count = 0
        req_count = 0
        review_count = 0

        logs = ["========================================", "LEGACY CONTRACT MIGRATION SUMMARY", "========================================"]

        for contract in contracts:
            p_count += 1
            # Determine sites to map
            sites_to_map = contract.contract_site_ids.mapped("site_id")
            if not sites_to_map and contract.site_id:
                sites_to_map = contract.site_id
            elif not sites_to_map:
                # Client-wide contract: find all active sites under this client
                sites_to_map = self.env["security.client.site"].search([
                    ("partner_id", "=", contract.partner_id.id),
                    ("active", "=", True),
                ])

            if not sites_to_map:
                logs.append(f"• Contract {contract.name} ({contract.partner_id.name}): No sites found. Flagged for review.")
                review_count += 1
                continue

            for site in sites_to_map:
                # Check if contract site line already exists for this site
                existing_c_site = contract.contract_site_ids.filtered(lambda cs: cs.site_id.id == site.id)
                if not existing_c_site:
                    existing_c_site = c_site_model.create({
                        "contract_id": contract.id,
                        "site_id": site.id,
                        "name": site.name,
                        "code": site.code,
                        "location": site.location,
                        "site_type": site.site_type or "commercial",
                        "supervisor_id": site.supervisor_id.id if site.supervisor_id else False,
                        "contact_name": site.contact_name,
                        "contact_phone": site.contact_phone,
                        "contact_email": site.contact_email,
                        "note": site.note,
                    })
                    s_count += 1
                else:
                    existing_c_site = existing_c_site[0]

                # Mark site as contract-managed
                site.write({
                    "contract_id": contract.id,
                    "is_contract_managed": True,
                })

                # Map posts
                for post in site.post_ids:
                    existing_c_post = existing_c_site.post_line_ids.filtered(lambda cp: cp.post_id.id == post.id)
                    if not existing_c_post:
                        existing_c_post = c_post_model.create({
                            "contract_site_id": existing_c_site.id,
                            "post_id": post.id,
                            "name": post.name,
                            "code": post.code,
                            "post_type_id": post.post_type_id.id if post.post_type_id else False,
                            "required_guard_count": post.required_guard_count or 1,
                        })
                        post_count += 1
                    else:
                        existing_c_post = existing_c_post[0]

                    post.write({
                        "contract_post_id": existing_c_post.id,
                        "is_contract_managed": True,
                    })

                    # Map shift requirements
                    for req in post.shift_requirement_ids:
                        existing_c_req = existing_c_post.requirement_line_ids.filtered(lambda cr: cr.requirement_id.id == req.id)
                        if not existing_c_req:
                            existing_c_req = c_req_model.create({
                                "contract_site_id": existing_c_site.id,
                                "contract_post_id": existing_c_post.id,
                                "requirement_id": req.id,
                                "shift_template_id": req.shift_template_id.id,
                                "guard_count": req.guard_count,
                                "monday": req.monday,
                                "tuesday": req.tuesday,
                                "wednesday": req.wednesday,
                                "thursday": req.thursday,
                                "friday": req.friday,
                                "saturday": req.saturday,
                                "sunday": req.sunday,
                                "bill_rate": req.bill_rate,
                                "pay_rate": req.pay_rate,
                                "rate_multiplier": req.rate_multiplier,
                                "fairness_weight": req.fairness_weight,
                                "preferred_employee_id": req.preferred_employee_id.id if req.preferred_employee_id else False,
                                "allow_preferred_only": req.allow_preferred_only,
                            })
                            req_count += 1
                        else:
                            existing_c_req = existing_c_req[0]

                        req.write({
                            "contract_requirement_id": existing_c_req.id,
                            "is_contract_managed": True,
                        })

        logs.append("")
        logs.append(f"Contracts processed:      {p_count}")
        logs.append(f"Sites mapped:             {s_count}")
        logs.append(f"Posts mapped:             {post_count}")
        logs.append(f"Requirements mapped:      {req_count}")
        logs.append(f"Needs review:             {review_count}")

        self.write({
            "state": "done",
            "contracts_processed": p_count,
            "sites_mapped": s_count,
            "posts_mapped": post_count,
            "requirements_mapped": req_count,
            "needs_review": review_count,
            "report_text": "\n".join(logs),
        })

        return {
            "type": "ir.actions.act_window",
            "res_model": "security.legacy.contract.migration.wizard",
            "res_id": self.id,
            "views": [[False, "form"]],
            "target": "new",
        }
