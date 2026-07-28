# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SecurityTourDefinition(models.Model):
    _name = 'security.tour.definition'
    _description = 'DeployGuard Product Tour Definition'
    _order = 'sequence, id'

    name = fields.Char(string="Tour Name", required=True)
    technical_name = fields.Char(string="Tour Technical Identifier", required=True)
    sequence = fields.Integer(string="Sequence", default=10)
    category = fields.Selection([
        ('prospect', 'Prospect Demo'),
        ('supervisor', 'Supervisor Onboarding'),
        ('manager', 'Manager Onboarding'),
        ('owner', 'Executive / Owner Onboarding'),
    ], string="Target Audience / Role", default='prospect', required=True)
    description = fields.Text(string="Description / Overview")
    estimated_minutes = fields.Integer(string="Estimated Duration (Minutes)", default=3)
    step_count = fields.Integer(string="Step Count", default=5)
    icon_class = fields.Char(string="FontAwesome Icon Class", default="fa-compass")
    start_url = fields.Char(string="Start URL / Action", default="/web")
    active = fields.Boolean(string="Active", default=True)

    @api.model
    def get_available_tours_rpc(self):
        """
        Returns list of active tours for the Systray launcher dropdown.
        """
        user = self.env.user
        tours = self.search([('active', '=', True)])
        res = []
        for tour in tours:
            # Check user completion status
            done = False
            if tour.technical_name == 'deployguard_prospect_demo_tour':
                done = user.tour_prospect_demo_done
            elif tour.technical_name == 'deployguard_supervisor_tour':
                done = user.tour_supervisor_done
            elif tour.technical_name == 'deployguard_manager_tour':
                done = user.tour_manager_done
            elif tour.technical_name == 'deployguard_owner_tour':
                done = user.tour_owner_done

            res.append({
                'id': tour.id,
                'technical_name': tour.technical_name,
                'name': tour.name,
                'category': tour.category,
                'description': tour.description,
                'estimated_minutes': tour.estimated_minutes,
                'step_count': tour.step_count,
                'icon_class': tour.icon_class,
                'done': done,
            })
        return res
