# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    tour_prospect_demo_done = fields.Boolean(
        string="Prospect Demo Tour Completed",
        default=False,
        help="Flag set when the user completes or dismisses the 3-minute Prospect Demo Tour."
    )
    tour_supervisor_done = fields.Boolean(
        string="Supervisor Onboarding Tour Completed",
        default=False,
        help="Flag set when the user completes or dismisses the Supervisor Onboarding Tour."
    )
    tour_manager_done = fields.Boolean(
        string="Manager Onboarding Tour Completed",
        default=False,
        help="Flag set when the user completes or dismisses the Manager Onboarding Tour."
    )
    tour_owner_done = fields.Boolean(
        string="Owner Onboarding Tour Completed",
        default=False,
        help="Flag set when the user completes or dismisses the Owner Onboarding Tour."
    )
    tour_auto_launch_enabled = fields.Boolean(
        string="Enable Automatic Onboarding Tours",
        default=True,
        help="If checked, pending onboarding tours will trigger automatically upon login."
    )

    @api.model
    def get_pending_user_tour(self):
        """
        Determines if there is a pending tour for the current logged-in user
        based on user groups / demo credentials and completion state.
        Returns dictionary with tour_id or False.
        """
        user = self.env.user
        if not user.tour_auto_launch_enabled:
            return {'pending_tour': False}

        login = (user.login or '').lower()
        
        # 1. Prospect Demo Tour for demo accounts / viewers
        if ('demo' in login or user.has_group('base.group_user')) and not user.tour_prospect_demo_done:
            # First priority for demo viewer / admin when demo tour is pending
            if login in ['demo.viewer@dogforce.demo', 'demo.admin@dogforce.demo'] or 'demo' in login:
                return {
                    'pending_tour': 'deployguard_prospect_demo_tour',
                    'tour_name': 'Prospect Demo Tour',
                    'tour_type': 'prospect'
                }

        # 2. Supervisor Onboarding Tour
        if user.has_group('security_base.group_security_supervisor') and not user.tour_supervisor_done:
            return {
                'pending_tour': 'deployguard_supervisor_tour',
                'tour_name': 'Supervisor Onboarding Tour',
                'tour_type': 'supervisor'
            }

        # 3. Manager Onboarding Tour
        if user.has_group('security_base.group_security_manager') and not user.tour_manager_done:
            return {
                'pending_tour': 'deployguard_manager_tour',
                'tour_name': 'Manager Onboarding Tour',
                'tour_type': 'manager'
            }

        # 4. Owner Onboarding Tour
        if user.has_group('security_base.group_security_owner') and not user.tour_owner_done:
            return {
                'pending_tour': 'deployguard_owner_tour',
                'tour_name': 'Executive Command Tour',
                'tour_type': 'owner'
            }

        return {'pending_tour': False}

    @api.model
    def action_complete_tour(self, tour_id):
        """
        Marks a specific tour as completed for the current user.
        """
        user = self.env.user
        if tour_id == 'deployguard_prospect_demo_tour':
            user.sudo().write({'tour_prospect_demo_done': True})
        elif tour_id == 'deployguard_supervisor_tour':
            user.sudo().write({'tour_supervisor_done': True})
        elif tour_id == 'deployguard_manager_tour':
            user.sudo().write({'tour_manager_done': True})
        elif tour_id == 'deployguard_owner_tour':
            user.sudo().write({'tour_owner_done': True})
        return True

    def action_reset_all_tours(self):
        """
        Resets tour progress for current user so they can replay onboarding tours.
        """
        self.ensure_one()
        self.write({
            'tour_prospect_demo_done': False,
            'tour_supervisor_done': False,
            'tour_manager_done': False,
            'tour_owner_done': False,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Product Tours Reset',
                'message': 'All onboarding tour flags have been reset. You can now replay any tour.',
                'type': 'success',
                'sticky': False,
            }
        }
