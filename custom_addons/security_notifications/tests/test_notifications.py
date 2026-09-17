from odoo.tests.common import TransactionCase
from datetime import date, timedelta


class TestSecurityNotifications(TransactionCase):

    def setUp(self):
        super().setUp()

        # Create a test employee/guard
        self.employee = self.env["hr.employee"].create({
            "name": "Festus Amadhila",
            "security_guard": True,
        })

        # Create a certification type
        self.cert_type = self.env["security.certification"].create({
            "name": "First Aid & Firefighting",
            "code": "FA_FF",
            "expiry_required": True,
        })

    def test_01_certification_expiry_scanner_creates_notifications(self):
        """Verify that certifications expiring within 30 days trigger notifications correctly."""
        # 1. Create a certification expiring in 15 days (should trigger alert)
        exp_15_days = date.today() + timedelta(days=15)
        cert_exp_soon = self.env["security.employee.certification"].create({
            "employee_id": self.employee.id,
            "certification_id": self.cert_type.id,
            "expiry_date": exp_15_days,
            "verified": True,
        })

        # 2. Create a certification expiring in 60 days (should NOT trigger alert)
        exp_60_days = date.today() + timedelta(days=60)
        cert_exp_far = self.env["security.employee.certification"].create({
            "employee_id": self.employee.id,
            "certification_id": self.cert_type.id,
            "expiry_date": exp_60_days,
            "verified": True,
        })

        # Run the scanner
        self.env["security.notification"].action_scan_certification_expiry()

        # Search for notifications matching our expiring soon certificate
        notifications = self.env["security.notification"].search([
            ("notification_type", "=", "cert_expiry"),
            ("related_model", "=", "security.employee.certification"),
            ("related_id", "=", cert_exp_soon.id),
        ])

        self.assertEqual(len(notifications), 1, "Should have created exactly one notification for the expiring soon cert.")
        notification = notifications[0]
        self.assertIn("First Aid & Firefighting", notification.title)
        self.assertIn("Festus Amadhila", notification.title)
        self.assertEqual(notification.severity, "warning", "Should be warning severity since 15 days remains (greater than 14).")

        # Verify that a notification was NOT created for the far certification
        no_notifications = self.env["security.notification"].search([
            ("notification_type", "=", "cert_expiry"),
            ("related_model", "=", "security.employee.certification"),
            ("related_id", "=", cert_exp_far.id),
        ])
        self.assertEqual(len(no_notifications), 0, "No notification should be created for certifications expiring beyond 30 days.")

    def test_02_certification_expiry_critical_severity(self):
        """Verify critical severity is raised when days left is <= 14."""
        exp_5_days = date.today() + timedelta(days=5)
        cert_exp_critical = self.env["security.employee.certification"].create({
            "employee_id": self.employee.id,
            "certification_id": self.cert_type.id,
            "expiry_date": exp_5_days,
            "verified": True,
        })

        # Run the scanner
        self.env["security.notification"].action_scan_certification_expiry()

        notifications = self.env["security.notification"].search([
            ("notification_type", "=", "cert_expiry"),
            ("related_model", "=", "security.employee.certification"),
            ("related_id", "=", cert_exp_critical.id),
        ])
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0].severity, "critical", "Should be critical severity when days left <= 14.")

    def test_03_no_duplicate_notifications(self):
        """Verify that running the scanner twice does not create duplicate notifications."""
        exp_10_days = date.today() + timedelta(days=10)
        cert_exp_soon = self.env["security.employee.certification"].create({
            "employee_id": self.employee.id,
            "certification_id": self.cert_type.id,
            "expiry_date": exp_10_days,
            "verified": True,
        })

        # Run once
        self.env["security.notification"].action_scan_certification_expiry()
        count_1 = self.env["security.notification"].search_count([
            ("notification_type", "=", "cert_expiry"),
            ("related_model", "=", "security.employee.certification"),
            ("related_id", "=", cert_exp_soon.id),
        ])
        self.assertEqual(count_1, 1)

        # Run again
        self.env["security.notification"].action_scan_certification_expiry()
        count_2 = self.env["security.notification"].search_count([
            ("notification_type", "=", "cert_expiry"),
            ("related_model", "=", "security.employee.certification"),
            ("related_id", "=", cert_exp_soon.id),
        ])
        self.assertEqual(count_2, 1, "Duplicate notifications should not be created on repeated runs.")
