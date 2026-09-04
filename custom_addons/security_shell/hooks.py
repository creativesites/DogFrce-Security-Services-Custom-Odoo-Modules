import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """DeployGuard Shell installed successfully.

    We deliberately do NOT redirect users to a specific home action here.
    The shell is a transparent layout enhancement — it wraps every Odoo page
    via template inheritance and the WebClient patch, so users land on whatever
    home they already had and the rail + nav panel simply appear around it.

    Setting action_id on every user would create a hard dependency: if this
    module is ever uninstalled, every user gets a broken home screen because
    the 'deployguard.main_command_center' tag would be unregistered.
    """
    _logger.info("DeployGuard Shell: installed. No user home actions modified.")

