import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Point every user still on the old fullscreen Command Center action
    (or with no home action at all) at the shell-wrapped Home dashboard.

    Users who deliberately picked a different home action keep it.
    """
    action = env.ref(
        "security_base.action_deployguard_main_command_center",
        raise_if_not_found=False,
    )
    if not action:
        _logger.warning(
            "DeployGuard Shell: home action xmlid not found, skipping post_init_hook."
        )
        return

    users = env["res.users"].search([
        ("share", "=", False),
        "|",
        ("action_id", "=", False),
        ("action_id", "=", action.id),
    ])
    if users:
        users.write({"action_id": action.id})

    default_user = env.ref("base.default_user", raise_if_not_found=False)
    if default_user and not default_user.action_id:
        default_user.sudo().write({"action_id": action.id})
