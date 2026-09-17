import base64

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, tagged

TINY_PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 100)


@tagged("post_install", "-at_install")
class TestEvidenceSizeLimit(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({"name": "Evidence Test Guard"})
        cls.template = cls.env["security.work.checklist.template"].create({
            "name": "Evidence Test Checklist",
            "item_ids": [(0, 0, {"label": "Photo", "item_type": "photo", "required": False})],
        })
        cls.task = cls.env["security.work.task"].create({
            "name": "Evidence Test Task", "employee_id": cls.employee.id,
            "checklist_template_id": cls.template.id,
        })

    def _response(self):
        return self.env["security.work.checklist.response"].search([
            ("task_id", "=", self.task.id)
        ], limit=1)

    def test_small_photo_is_accepted(self):
        self._response().write({"photo": TINY_PNG.decode()})
        self.assertTrue(self._response().photo)

    def test_oversized_photo_is_rejected(self):
        oversized = base64.b64encode(b"0" * (9 * 1024 * 1024)).decode()
        with self.assertRaises(ValidationError):
            self._response().write({"photo": oversized})

    def test_empty_photo_is_always_fine(self):
        self._response().write({"photo": False})
        self.assertFalse(self._response().photo)


@tagged("post_install", "-at_install")
class TestEvidenceRetention(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({"name": "Retention Test Guard"})
        cls.template = cls.env["security.work.checklist.template"].create({
            "name": "Retention Test Checklist",
            "item_ids": [(0, 0, {"label": "Photo", "item_type": "photo", "required": False})],
        })

    def _task_with_photo(self, state):
        task = self.env["security.work.task"].create({
            "name": "Retention Test Task", "employee_id": self.employee.id,
            "checklist_template_id": self.template.id, "state": state,
        })
        response = self.env["security.work.checklist.response"].search([("task_id", "=", task.id)], limit=1)
        response.write({"photo": TINY_PNG.decode()})
        return task, response

    def test_old_verified_task_evidence_is_purged(self):
        task, response = self._task_with_photo("verified")
        self.env.cr.execute(
            "UPDATE security_work_task SET write_date = write_date - interval '400 days' WHERE id = %s",
            (task.id,),
        )
        self.env["security.work.checklist.response"].action_purge_old_evidence()
        response.invalidate_recordset()
        self.assertFalse(response.photo)

    def test_recent_verified_task_evidence_is_kept(self):
        task, response = self._task_with_photo("verified")
        self.env["security.work.checklist.response"].action_purge_old_evidence()
        response.invalidate_recordset()
        self.assertTrue(response.photo)

    def test_open_task_evidence_is_never_purged_regardless_of_age(self):
        task, response = self._task_with_photo("open")
        self.env.cr.execute(
            "UPDATE security_work_task SET write_date = write_date - interval '400 days' WHERE id = %s",
            (task.id,),
        )
        self.env["security.work.checklist.response"].action_purge_old_evidence()
        response.invalidate_recordset()
        self.assertTrue(response.photo, "an in-progress task's evidence must never be purged")


@tagged("post_install", "-at_install")
class TestChecklistResponseAccessControl(TransactionCase):
    """Phase 3.10 audit: the response model previously had no record rule
    at all."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_a = cls.env["res.users"].create({
            "name": "Response ACL Guard A", "login": "response-acl-a@access-control.test",
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
        })
        cls.user_b = cls.env["res.users"].create({
            "name": "Response ACL Guard B", "login": "response-acl-b@access-control.test",
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
        })
        cls.employee_a = cls.env["hr.employee"].create({
            "name": "Response ACL Guard A", "user_id": cls.user_a.id,
        })
        cls.employee_b = cls.env["hr.employee"].create({
            "name": "Response ACL Guard B", "user_id": cls.user_b.id,
        })
        cls.template = cls.env["security.work.checklist.template"].create({
            "name": "ACL Test Checklist",
            "item_ids": [(0, 0, {"label": "Item", "item_type": "boolean"})],
        })
        cls.task_b = cls.env["security.work.task"].create({
            "name": "B's task", "employee_id": cls.employee_b.id,
            "checklist_template_id": cls.template.id,
        })
        cls.response_b = cls.env["security.work.checklist.response"].search(
            [("task_id", "=", cls.task_b.id)], limit=1
        )

    def test_user_cannot_read_another_employees_response(self):
        found = self.env["security.work.checklist.response"].with_user(self.user_a).search(
            [("id", "=", self.response_b.id)]
        )
        self.assertFalse(found)

    def test_user_cannot_write_another_employees_response(self):
        with self.assertRaises(AccessError):
            self.response_b.with_user(self.user_a).write({"value_bool": True})

    def test_supervisor_can_see_every_response(self):
        supervisor = self.env["res.users"].create({
            "name": "Response ACL Supervisor", "login": "response-acl-supervisor@access-control.test",
            "group_ids": [(6, 0, [self.env.ref("security_work.group_work_supervisor").id])],
        })
        found = self.env["security.work.checklist.response"].with_user(supervisor).search(
            [("id", "=", self.response_b.id)]
        )
        self.assertEqual(found, self.response_b)
