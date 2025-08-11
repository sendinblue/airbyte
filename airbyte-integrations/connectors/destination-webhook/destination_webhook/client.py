from typing import Any, Mapping, List
from logging import getLogger

import requests

logger = getLogger("airbyte")


class WebhookClient:
    def __init__(
        self,
        url: str,
        batch_size: int = 50,
    ) -> None:
        self.url = url
        self.batch_size = batch_size
        self.write_buffer = []

    def _request(self, http_method: str = "PUT", data: List[Mapping] = None) -> requests.Response:
        response = requests.request(method=http_method, url=self.url, json=data)
        return response

    def check_url(self) -> requests.Response:
        return self._request("GET")  

    def write(self, request_body: List[Mapping]):
        return self._request("POST", request_body)

    def queue_write_operation(self, record: Mapping):
        self.write_buffer.append(record)
        if len(self.write_buffer) == self.batch_size:
            self.write(self.write_buffer)
            self.write_buffer.clear()