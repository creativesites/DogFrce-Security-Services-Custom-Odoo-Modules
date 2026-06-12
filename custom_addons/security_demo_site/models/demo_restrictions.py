from odoo import models, api
from odoo.exceptions import UserError
from odoo.tools.translate import _

_VIEWER = 'security_demo_site.group_demo_viewer'
_NO_DELETE = 'security_demo_site.group_demo_no_delete'

_MSG_VIEWER = "Demo Viewer is a read-only account. Log in as Operations Manager or Field Operator to make changes."
_MSG_DELETE = "Demo accounts cannot delete records — this protects the live demo data."


def _block_viewer(env):
    if env.user.has_group(_VIEWER):
        raise UserError(_(_MSG_VIEWER))


def _block_delete(env):
    if env.user.has_group(_VIEWER) or env.user.has_group(_NO_DELETE):
        raise UserError(_(_MSG_DELETE))


# ── Operational models ────────────────────────────────────────────────────────

class HrEmployeeDemo(models.Model):
    _inherit = 'hr.employee'

    @api.model_create_multi
    def create(self, vals_list):
        _block_viewer(self.env)
        return super().create(vals_list)

    def write(self, vals):
        _block_viewer(self.env)
        return super().write(vals)

    def unlink(self):
        _block_delete(self.env)
        return super().unlink()


class SecurityPostDemo(models.Model):
    _inherit = 'security.post'

    @api.model_create_multi
    def create(self, vals_list):
        _block_viewer(self.env)
        return super().create(vals_list)

    def write(self, vals):
        _block_viewer(self.env)
        return super().write(vals)

    def unlink(self):
        _block_delete(self.env)
        return super().unlink()


class SecurityPostTypeDemo(models.Model):
    _inherit = 'security.post.type'

    @api.model_create_multi
    def create(self, vals_list):
        _block_viewer(self.env)
        return super().create(vals_list)

    def write(self, vals):
        _block_viewer(self.env)
        return super().write(vals)

    def unlink(self):
        _block_delete(self.env)
        return super().unlink()


class SecurityClientSiteDemo(models.Model):
    _inherit = 'security.client.site'

    @api.model_create_multi
    def create(self, vals_list):
        _block_viewer(self.env)
        return super().create(vals_list)

    def write(self, vals):
        _block_viewer(self.env)
        return super().write(vals)

    def unlink(self):
        _block_delete(self.env)
        return super().unlink()


class SecurityAttendanceRecordDemo(models.Model):
    _inherit = 'security.attendance.record'

    @api.model_create_multi
    def create(self, vals_list):
        _block_viewer(self.env)
        return super().create(vals_list)

    def write(self, vals):
        _block_viewer(self.env)
        return super().write(vals)

    def unlink(self):
        _block_delete(self.env)
        return super().unlink()


class SecurityAttendanceBatchDemo(models.Model):
    _inherit = 'security.attendance.batch'

    @api.model_create_multi
    def create(self, vals_list):
        _block_viewer(self.env)
        return super().create(vals_list)

    def write(self, vals):
        _block_viewer(self.env)
        return super().write(vals)

    def unlink(self):
        _block_delete(self.env)
        return super().unlink()


class SecurityRosterSlotDemo(models.Model):
    _inherit = 'security.roster.slot'

    @api.model_create_multi
    def create(self, vals_list):
        _block_viewer(self.env)
        return super().create(vals_list)

    def write(self, vals):
        _block_viewer(self.env)
        return super().write(vals)

    def unlink(self):
        _block_delete(self.env)
        return super().unlink()


class SecurityRosterBatchDemo(models.Model):
    _inherit = 'security.roster.batch'

    @api.model_create_multi
    def create(self, vals_list):
        _block_viewer(self.env)
        return super().create(vals_list)

    def write(self, vals):
        _block_viewer(self.env)
        return super().write(vals)

    def unlink(self):
        _block_delete(self.env)
        return super().unlink()


class SecurityLeaveRequestDemo(models.Model):
    _inherit = 'security.leave.request'

    @api.model_create_multi
    def create(self, vals_list):
        _block_viewer(self.env)
        return super().create(vals_list)

    def write(self, vals):
        _block_viewer(self.env)
        return super().write(vals)

    def unlink(self):
        _block_delete(self.env)
        return super().unlink()


class SecurityLeaveTypeDemo(models.Model):
    _inherit = 'security.leave.type'

    @api.model_create_multi
    def create(self, vals_list):
        _block_viewer(self.env)
        return super().create(vals_list)

    def write(self, vals):
        _block_viewer(self.env)
        return super().write(vals)

    def unlink(self):
        _block_delete(self.env)
        return super().unlink()


class SecurityIncidentDemo(models.Model):
    _inherit = 'security.incident'

    @api.model_create_multi
    def create(self, vals_list):
        _block_viewer(self.env)
        return super().create(vals_list)

    def write(self, vals):
        _block_viewer(self.env)
        return super().write(vals)

    def unlink(self):
        _block_delete(self.env)
        return super().unlink()


class SecurityBillingInvoiceDemo(models.Model):
    _inherit = 'security.billing.invoice'

    @api.model_create_multi
    def create(self, vals_list):
        _block_viewer(self.env)
        return super().create(vals_list)

    def write(self, vals):
        _block_viewer(self.env)
        return super().write(vals)

    def unlink(self):
        _block_delete(self.env)
        return super().unlink()


class SecurityBillingPlanDemo(models.Model):
    _inherit = 'security.billing.plan'

    @api.model_create_multi
    def create(self, vals_list):
        _block_viewer(self.env)
        return super().create(vals_list)

    def write(self, vals):
        _block_viewer(self.env)
        return super().write(vals)

    def unlink(self):
        _block_delete(self.env)
        return super().unlink()


class SecurityPayslipDemo(models.Model):
    _inherit = 'security.payslip'

    @api.model_create_multi
    def create(self, vals_list):
        _block_viewer(self.env)
        return super().create(vals_list)

    def write(self, vals):
        _block_viewer(self.env)
        return super().write(vals)

    def unlink(self):
        _block_delete(self.env)
        return super().unlink()


class SecurityPayrollPeriodDemo(models.Model):
    _inherit = 'security.payroll.period'

    @api.model_create_multi
    def create(self, vals_list):
        _block_viewer(self.env)
        return super().create(vals_list)

    def write(self, vals):
        _block_viewer(self.env)
        return super().write(vals)

    def unlink(self):
        _block_delete(self.env)
        return super().unlink()


class SecurityEquipmentItemDemo(models.Model):
    _inherit = 'security.equipment.item'

    @api.model_create_multi
    def create(self, vals_list):
        _block_viewer(self.env)
        return super().create(vals_list)

    def write(self, vals):
        _block_viewer(self.env)
        return super().write(vals)

    def unlink(self):
        _block_delete(self.env)
        return super().unlink()


class SecurityVehicleDemo(models.Model):
    _inherit = 'security.vehicle'

    @api.model_create_multi
    def create(self, vals_list):
        _block_viewer(self.env)
        return super().create(vals_list)

    def write(self, vals):
        _block_viewer(self.env)
        return super().write(vals)

    def unlink(self):
        _block_delete(self.env)
        return super().unlink()


class SecurityShiftTemplateDemo(models.Model):
    _inherit = 'security.shift.template'

    @api.model_create_multi
    def create(self, vals_list):
        _block_viewer(self.env)
        return super().create(vals_list)

    def write(self, vals):
        _block_viewer(self.env)
        return super().write(vals)

    def unlink(self):
        _block_delete(self.env)
        return super().unlink()


class SecurityGradeDemo(models.Model):
    _inherit = 'security.grade'

    @api.model_create_multi
    def create(self, vals_list):
        _block_viewer(self.env)
        return super().create(vals_list)

    def write(self, vals):
        _block_viewer(self.env)
        return super().write(vals)

    def unlink(self):
        _block_delete(self.env)
        return super().unlink()


class SecurityPublicHolidayDemo(models.Model):
    _inherit = 'security.public.holiday'

    @api.model_create_multi
    def create(self, vals_list):
        _block_viewer(self.env)
        return super().create(vals_list)

    def write(self, vals):
        _block_viewer(self.env)
        return super().write(vals)

    def unlink(self):
        _block_delete(self.env)
        return super().unlink()
