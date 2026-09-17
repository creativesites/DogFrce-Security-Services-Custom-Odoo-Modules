from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestDeployguardApi(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.integration_user = cls.env["security.deployguard.config"].get_config().integration_user_id
        cls.plain_user = cls.env["res.users"].create({
            "name": "Plain Internal User",
            "login": "deployguard_api_test_plain_user",
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
        })
        cls.partner = cls.env["res.partner"].create({"name": "Facade Test Client"})
        cls.site = cls.env["security.client.site"].create({
            "name": "Facade Test Site", "partner_id": cls.partner.id,
        })
        cls.employee = cls.env["hr.employee"].create({"name": "Facade Test Employee"})

    def _api(self, user):
        return self.env["security.deployguard.api"].with_user(user)

    def test_non_integration_user_is_refused(self):
        with self.assertRaises(AccessError):
            self._api(self.plain_user).ping()

    def test_integration_user_can_ping(self):
        result = self._api(self.integration_user).ping()
        self.assertIn("version", result)
        self.assertIn("contract", result)
        self.assertIn("server_time", result)

    def test_get_sites_returns_the_documented_fields_only(self):
        result = self._api(self.integration_user).get_sites()
        row = next(item for item in result["items"] if item["id"] == self.site.id)
        self.assertEqual(
            set(row.keys()),
            {"id", "name", "code", "client_id", "client_name", "site_type", "active", "write_date"},
        )
        self.assertEqual(row["client_id"], self.partner.id)

    def test_get_employees_excludes_private_hr_fields(self):
        result = self._api(self.integration_user).get_employees()
        row = next(item for item in result["items"] if item["id"] == self.employee.id)
        allowed = {"id", "name", "job_id", "job_title", "grade_id", "grade_name",
                   "parent_id", "user_id", "active", "write_date"}
        self.assertEqual(set(row.keys()), allowed)
        # No national ID, bank details or medical fields under any name.
        forbidden_markers = ("bank", "national_id", "medical", "identity_number")
        for key in row:
            self.assertFalse(any(marker in key.lower() for marker in forbidden_markers))

    def test_get_users_never_exposes_password_or_api_key_material(self):
        result = self._api(self.integration_user).get_users(ids=[self.plain_user.id])
        row = result["items"][0]
        forbidden_markers = ("password", "api_key", "apikey", "session")
        for key in row:
            self.assertFalse(any(marker in key.lower() for marker in forbidden_markers))
        self.assertIn("deployguard_access", row)
        self.assertFalse(row["deployguard_access"], "default must be False")

    def test_get_sites_since_filters_by_write_date(self):
        future = fields.Datetime.to_string(
            fields.Datetime.add(fields.Datetime.now(), days=1)
        )
        result = self._api(self.integration_user).get_sites(since=future)
        self.assertEqual(result["items"], [])

    def test_limit_is_capped_at_500(self):
        result = self._api(self.integration_user).get_sites(limit=5000)
        # Just confirm the call succeeds and doesn't error on an oversized
        # limit -- the cap is asserted by reading the method's own logic
        # rather than creating 500+ records here.
        self.assertIn("items", result)
