def set_security_home_action(env):
    """Set the Executive Dashboard as the home action for all internal users."""
    action = env.ref(
        "security_reporting.action_security_executive_dashboard",
        raise_if_not_found=False,
    )
    if not action:
        return
    users = env["res.users"].search([("share", "=", False), ("active", "=", True)])
    users.write({"action_id": action.id})

    # Also apply to the default user template so new users get the same home
    default_user = env.ref("base.default_user", raise_if_not_found=False)
    if default_user:
        default_user.sudo().write({"action_id": action.id})
