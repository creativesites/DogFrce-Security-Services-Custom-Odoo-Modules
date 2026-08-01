from odoo.tests.common import TransactionCase


class TestReconciliationCore(TransactionCase):
    def setUp(self):
        super().setUp()
        self.rule = self.env["security.reconciliation.rule"].create({
            "name": "Test reconciliation rule",
            "adapter_code": "test_core",
            "source_model": "security.billing.invoice",
            "target_model": "account.move",
            "company_id": self.env.company.id,
        })

    def test_link_is_unique_per_rule_and_source(self):
        values = {
            "rule_id": self.rule.id,
            "source_model": "security.billing.invoice",
            "source_res_id": 101,
            "target_model": "account.move",
            "target_res_id": 201,
        }
        self.env["security.reconciliation.link"].create(values)
        with self.assertRaises(Exception):
            self.env["security.reconciliation.link"].create(values)

    def test_unconfigured_job_is_retried_and_logged(self):
        job = self.env["security.reconciliation.job"].create({
            "rule_id": self.rule.id,
            "origin_model": "security.billing.invoice",
            "origin_res_id": 101,
        })
        job.action_dispatch_jobs()
        self.assertEqual(job.state, "retry")
        self.assertEqual(job.attempt_count, 1)
        self.assertTrue(job.log_ids)
