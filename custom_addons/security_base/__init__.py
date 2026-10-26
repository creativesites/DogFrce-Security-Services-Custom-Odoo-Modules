import odoo.http

# Harden session lifetime to 90 days (3 months = 7,776,000 seconds)
# Prevents operational staff from being repeatedly logged out on Monday mornings
odoo.http.SESSION_LIFETIME = 60 * 60 * 24 * 90

from . import models
from .hooks import post_init_hook
