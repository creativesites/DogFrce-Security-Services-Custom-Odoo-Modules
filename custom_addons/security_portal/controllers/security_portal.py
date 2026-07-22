import logging
from odoo import http, fields, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class SecurityPortalController(http.Controller):

    @http.route(["/my/security-dashboard"], type="http", auth="user", website=True)
    def security_dashboard(self, **kwargs):
        """
        Renders the premium real-time Client Operations Portal Dashboard for security site managers.
        """
        partner = request.env.user.partner_id

        # Query all sites belonging to the logged-in portal partner (or parent company)
        sites = request.env["security.client.site"].search([
            "|",
            ("partner_id", "=", partner.id),
            ("partner_id", "=", partner.parent_id.id),
        ])

        today = fields.Date.today()

        # Gather real-time posting statistics across all client sites for today
        roster_slots = request.env["security.roster.slot"].search([
            ("site_id", "in", sites.ids),
            ("shift_date", "=", today),
        ])

        total_posts = len(roster_slots)
        assigned_posts = len(roster_slots.filtered(lambda s: s.employee_id))
        unassigned_posts = total_posts - assigned_posts

        # Match attendance records for today to determine actual physical guard presence
        attendance_records = request.env["security.attendance"].search([
            ("site_id", "in", sites.ids),
            ("shift_date", "=", today),
        ])

        present_guards = len(attendance_records.filtered(lambda a: a.actual_check_in and not a.actual_check_out))
        completed_shifts = len(attendance_records.filtered(lambda a: a.actual_check_out))
        missing_guards = len(attendance_records.filtered(lambda a: a.state == "absent" or a.attendance_status == "awol"))

        stats = {
            "total_posts": total_posts,
            "assigned_posts": assigned_posts,
            "unassigned_posts": unassigned_posts,
            "present_guards": present_guards,
            "completed_shifts": completed_shifts,
            "missing_guards": missing_guards,
        }

        values = {
            "partner": partner,
            "sites": sites,
            "roster_slots": roster_slots,
            "stats": stats,
            "page_name": "security_dashboard",
            "success_message": kwargs.get("success_message"),
        }

        return request.render("security_portal.security_portal_dashboard", values)

    @http.route(["/my/security-dashboard/feedback"], type="http", auth="user", methods=["POST"], website=True, csrf=True)
    def submit_feedback(self, **post):
        """
        Processes real-time shift feedback and quality ratings submitted by the client site manager.
        """
        site_id = int(post.get("site_id", 0))
        rating = int(post.get("rating", 5))
        feedback = post.get("feedback", "")

        site = request.env["security.client.site"].browse(site_id)
        if not site:
            return request.redirect("/my/security-dashboard")

        # Verify portal user has ownership access to this site
        partner = request.env.user.partner_id
        if site.partner_id.id != partner.id and site.partner_id.parent_id.id != partner.id:
            return request.redirect("/my/security-dashboard")

        # Broadcast the feedback event on the DeployGuard Central Intelligence Bus
        payload = {
            "site_id": site.id,
            "rating": rating,
            "feedback": feedback,
            "manager_name": partner.name,
        }

        request.env["security.event.log"].register_event(
            name="portal.feedback_received",
            source_model="security.client.site",
            source_id=site.id,
            payload=payload,
        )

        return request.redirect("/my/security-dashboard?success_message=Feedback+submitted+successfully!+Thank+you.")
