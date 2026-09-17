{
    "name": "DeployGuard Bridge",
    "summary": "Core bridge between DeployGuard ERP (this Odoo) and the DeployGuard Platform",
    "version": "19.0.1.0.0",
    "category": "Security/Integration",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "description": """
        Core of the Odoo-side bridge described in
        docs/deployguard/adr/DG-ADR-018-odoo-bridge-addons.md. Explicit
        install per client (R-2/R-6) -- never auto-installed, and never on
        a client database that doesn't use the DeployGuard Platform.

        What ships in this slice (BUILD-ORDER P2, phase-plan Phase 2):
        - security.deployguard.config: settings singleton, webhook secret
          and bridge signing keypair, both encrypted at rest with a key
          that never lives in the database (docs/deployguard/adr/
          DG-ADR-018-odoo-bridge-addons.md §6).
        - group_deployguard_integration + a dedicated integration user,
          created on install with no usable password -- it authenticates
          to the Platform exclusively via an Odoo API key
          (res.users.apikeys), per docs/deployguard/12-odoo-integration.md
          §2 step 3. This bridge does not invent its own API-key scheme.
        - security.deployguard.outbox: signed, retried event delivery
          queue, modelled on security_reconciliation_core's job pattern.
        - security.deployguard.api: the read-only facade
          (ping/get_sites/get_employees/get_users), field-allowlisted per
          docs/deployguard/12-odoo-integration.md §3.

        Deliberately NOT in this slice -- see
        docs/deployguard/BUILD-STATUS-AND-PHASE-PLAN.md Phase 2:
        - The auth/SSO endpoints (auth/login, auth/totp, sso/ticket,
          sso/consume) from DG-ADR-007. That is security-critical,
          user-facing authentication code and deserves its own change,
          its own security review, and full HttpCase coverage of every
          negative case (wrong password, ticket replay, ticket expiry,
          admin-account refusal) before it ships -- not a slice of a
          larger commit. The signing keypair this module generates is
          exactly what that work will sign assertions with, so building
          it now is not wasted, but no endpoint reads it yet.
        - Domain bridges (attendance, roster, incidents, leave,
          notifications) -- next once this core is reviewed and installed
          on a real (non-production) database.
    """,
    "depends": ["security_base", "mail"],
    "data": [
        "security/security_groups.xml",
        "security/ir.model.access.csv",
        "data/security_deployguard_cron.xml",
        "views/security_deployguard_config_views.xml",
        "views/security_deployguard_outbox_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "auto_install": False,
}
