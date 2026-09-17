from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class SecurityDeployguardApiController(http.Controller):

    @http.route([
        '/json/2/security.deployguard.api/ping',
        '/json/2/security.deployguard.api/get_sites',
        '/json/2/security.deployguard.api/get_employees',
        '/json/2/security.deployguard.api/get_users'
    ], type='json', auth='none', methods=['POST'], csrf=False)
    def dispatch_facade(self, **kwargs):
        """
        Intercepts Platform API requests, authenticates the Bearer token,
        and safely delegates execution to the corresponding API facade method.
        """
        auth_header = request.httprequest.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            _logger.warning("DeployGuard API | Authentication Failed: Missing or invalid Authorization header.")
            return {"error": "Missing or invalid Authorization header"}
        
        token = auth_header.split(" ", 1)[1]

        # Standard Odoo API Key credential checker
        try:
            uid = request.env['res.users']._check_api_key(token)
            if not uid:
                _logger.warning("DeployGuard API | Authentication Failed: Invalid API key token.")
                return {"error": "Invalid API key"}
        except Exception as e:
            _logger.error("DeployGuard API | Odoo check_api_key Raised Exception: %s", e)
            return {"error": "Authentication processing error"}

        # Switch request environment to run as the authenticated integration user
        request.update_env(user=uid)

        # Retrieve the method name from path routing
        path = request.httprequest.path
        method_name = path.split('/')[-1]
        
        facade_model = request.env["security.deployguard.api"]
        if not hasattr(facade_model, method_name):
            _logger.error("DeployGuard API | Error: Method %s not found on the facade model.", method_name)
            return {"error": f"Method {method_name} not found"}

        method = getattr(facade_model, method_name)
        try:
            return method(**kwargs)
        except Exception as e:
            _logger.error("DeployGuard API | Method %s Execution Failed: %s", method_name, e)
            return {"error": f"Internal Facade Execution Failure: {str(e)}"}
