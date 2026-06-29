import json
import logging

_logger = logging.getLogger(__name__)


class ZRAApiError(Exception):
    pass


class ZRAApiClient:
    """HTTP client for the ZRA Smart Invoice (VSDC) REST API.

    Sandbox endpoint:    https://sandbox.zra.org.zm:38083/sandboxvsdc
    Production endpoint: https://vsdc.zra.org.zm:38085/vsdc
    Reference: ZRA Smart Invoice Integration Guide (VSDC API v1.3)
    """

    RESULT_OK = "000"

    def __init__(self, base_url, tpin, bhf_id, dvc_srl_no):
        self.base_url = base_url.rstrip("/")
        self.tpin = tpin
        self.bhf_id = bhf_id or "000"
        self.dvc_srl_no = dvc_srl_no

    def _headers(self):
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _post(self, path, payload):
        try:
            import requests as _req
        except ImportError:
            raise ZRAApiError("Python 'requests' library is not available in this environment.")
        url = f"{self.base_url}/{path}"
        payload.setdefault("tpin", self.tpin)
        payload.setdefault("bhfId", self.bhf_id)
        payload.setdefault("dvcSrlNo", self.dvc_srl_no)
        raw_request = json.dumps(payload)
        try:
            response = _req.post(
                url, data=raw_request, headers=self._headers(), timeout=30
            )
            response.raise_for_status()
            data = response.json()
        except _req.exceptions.Timeout:
            raise ZRAApiError("ZRA API timed out after 30 seconds.")
        except _req.exceptions.ConnectionError as exc:
            raise ZRAApiError(f"ZRA API connection failed: {exc}")
        except _req.exceptions.HTTPError:
            try:
                body = response.text[:300]
            except Exception:
                body = ""
            raise ZRAApiError(f"ZRA API HTTP {response.status_code}: {body}")
        except Exception as exc:
            raise ZRAApiError(f"ZRA API unexpected error: {exc}")
        raw_response = json.dumps(data)
        return raw_request, raw_response, data

    def get_info(self):
        """Ping the VSDC initializer to verify connectivity and credentials."""
        _, _, data = self._post("initializer/selectInitializer", {
            "lastReqDt": "20240101000000",
        })
        return data

    def save_sales(self, payload):
        """Submit a sale or credit note to ZRA VSDC.

        Returns (raw_request, raw_response, parsed_response_dict).
        Raises ZRAApiError if the network call fails or ZRA returns a non-000 result code.
        """
        raw_req, raw_resp, data = self._post("sales/saveSales", payload)
        if data.get("resultCd") != self.RESULT_OK:
            msg = data.get("resultMsg") or "Unknown error"
            raise ZRAApiError(
                f"ZRA rejected submission [{data.get('resultCd')}]: {msg}"
            )
        return raw_req, raw_resp, data
