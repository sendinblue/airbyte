import base64
import requests
from typing import Any, Mapping, List
from logging import getLogger

logger = getLogger("airbyte")


class PartnerStackClient:
    def __init__(self, public_key: str, private_key: str, pobject: str) -> None:
        self.public_key = public_key
        self.private_key = private_key
        self.endpoint = pobject["endpoint"]
        self.method = pobject["method"]
        self.key = pobject.get("key", None)

    def _get_base_url(self) -> str:
        return f"https://api.partnerstack.com/api/v2{self.endpoint}"

    def encode_base64(self, msg: str) -> str:
        message_bytes = msg.encode("ascii")
        base64_bytes = base64.b64encode(message_bytes)
        base64_message = base64_bytes.decode("ascii")
        return base64_message

    def _get_auth_headers(self) -> Mapping[str, Any]:
        auth_encode = self.encode_base64(f"{self.public_key}:{self.private_key}")
        return {"authorization": f"Basic {auth_encode}"}

    def write(self, request_body: List[Mapping]):
        return self._request(http_method=self.method, data=request_body)

    def update(self, key: str, request_body: List[Mapping]):
        url = self._get_base_url() + f"/{request_body[key]}"
        logger.info(url)
        request_body.pop(key, None)
        return self._request(http_method=self.method, url=url, data=request_body)

    def list(self):
        return self._request(http_method="GET")

    def _request(
        self,
        http_method: str,
        url: str = None,
        data: List[Mapping] = None,
    ) -> requests.Response:
        if url is None:
            url = self._get_base_url()
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            **self._get_auth_headers(),
        }
        response = requests.request(
            method=http_method, url=url, headers=headers, json=data
        )
        return response
