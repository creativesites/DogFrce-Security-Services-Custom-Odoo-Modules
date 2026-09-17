from odoo import fields, models
from odoo.exceptions import AccessError


class SecurityDeployguardApi(models.AbstractModel):
    """Read-only facade for the DeployGuard Platform.

    docs/deployguard/12-odoo-integration.md §3. Called over JSON-2
    (`POST {odoo}/json/2/security.deployguard.api/<method>`) authenticated
    as the DeployGuard Integration user via its Odoo API key. Every method:

    - checks the caller holds group_deployguard_integration explicitly.
      This model has no table (AbstractModel), so the usual
      ir.model.access read/write/create/unlink rows do not gate arbitrary
      method calls the way they would on a concrete model -- this check is
      the real access control here, not a backstop for one;
    - returns only the field allowlist the spec names, never "just in
      case" extras (12-odoo-integration.md §3's own rule);
    - reads with sudo() *inside* the method, scoped to exactly this query,
      rather than granting the integration group broad ACLs on domain
      models (DG-ADR-018 §3: "invoked with the minimum elevation required
      inside each method").

    Only the four MVP methods that need no other bridge module installed
    are here: ping, get_sites, get_employees, get_users. The roster/
    attendance/incidents/leave/alerts methods each belong with their domain
    bridge (DG-ADR-018's module table) once that bridge exists, so this
    facade grows alongside the modules that give it something real to read.
    """

    _name = "security.deployguard.api"
    _description = "DeployGuard Facade API"

    def _assert_integration_caller(self):
        if not self.env.user.has_group(
            "security_deployguard_bridge.group_deployguard_integration"
        ):
            raise AccessError(
                "Only the DeployGuard Integration user may call this API."
            )

    def ping(self):
        self._assert_integration_caller()
        config = self.env["security.deployguard.config"].sudo().get_config()
        return {
            "version": "1.0.0",
            "contract": config.contract_version,
            "db": self.env.cr.dbname,
            "server_time": fields.Datetime.to_string(fields.Datetime.now()),
            "tenant_id": config.tenant_id or False,
        }

    def get_sites(self, since=None, limit=500, cursor=None):
        self._assert_integration_caller()
        limit = min(limit or 500, 500)
        domain = []
        if since:
            domain.append(("write_date", ">", since))
        if cursor:
            domain.append(("id", ">", cursor))
        sites = self.env["security.client.site"].sudo().search(
            domain, limit=limit, order="id"
        )
        return {
            "items": [
                {
                    "id": site.id,
                    "name": site.name,
                    "code": site.code or False,
                    "client_id": site.partner_id.id,
                    "client_name": site.partner_id.name,
                    "site_type": site.site_type,
                    "active": site.active,
                    "write_date": fields.Datetime.to_string(site.write_date),
                }
                for site in sites
            ],
            "next_cursor": sites[-1].id if len(sites) == limit else False,
        }

    def get_employees(self, since=None, limit=500, cursor=None):
        """No private HR fields (national ID, bank details, medical
        documents) -- see 12-odoo-integration.md §3's own rule and
        docs/deployguard/00-current-state.md §7."""
        self._assert_integration_caller()
        limit = min(limit or 500, 500)
        domain = []
        if since:
            domain.append(("write_date", ">", since))
        if cursor:
            domain.append(("id", ">", cursor))
        employees = self.env["hr.employee"].sudo().search(domain, limit=limit, order="id")
        return {
            "items": [
                {
                    "id": emp.id,
                    "name": emp.name,
                    "job_id": emp.job_id.id if emp.job_id else False,
                    "job_title": emp.job_id.name if emp.job_id else False,
                    "grade_id": emp.security_grade_id.id if emp.security_grade_id else False,
                    "grade_name": emp.security_grade_id.name if emp.security_grade_id else False,
                    "parent_id": emp.parent_id.id if emp.parent_id else False,
                    "user_id": emp.user_id.id if emp.user_id else False,
                    "active": emp.active,
                    "write_date": fields.Datetime.to_string(emp.write_date),
                }
                for emp in employees
            ],
            "next_cursor": employees[-1].id if len(employees) == limit else False,
        }

    def get_users(self, ids=None, since=None, limit=500):
        """No password hashes, no API keys, no session data -- only what
        DG-ADR-007's identity linking and revocation polling need."""
        self._assert_integration_caller()
        limit = min(limit or 500, 500)
        domain = []
        if ids:
            domain.append(("id", "in", ids))
        if since:
            domain.append(("write_date", ">", since))
        users = self.env["res.users"].sudo().search(domain, limit=limit, order="id")
        return {
            "items": [
                {
                    "id": user.id,
                    "login": user.login,
                    "name": user.name,
                    "email": user.email or False,
                    "active": user.active,
                    "share": user.share,
                    "deployguard_access": user.deployguard_access,
                    "totp_enabled": bool(user.totp_enabled) if "totp_enabled" in user._fields else False,
                    "write_date": fields.Datetime.to_string(user.write_date),
                }
                for user in users
            ],
        }
