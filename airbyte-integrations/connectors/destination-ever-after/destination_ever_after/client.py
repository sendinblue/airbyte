from this import d
from typing import Any, Mapping, List
from logging import getLogger
import time

import requests

logger = getLogger("airbyte")

class EverAfterClient():
    def __init__(self, api_key: str, everafter_object: str) -> None:
        self.api_key = api_key
        self.everafter_object = everafter_object["value"]
        self.url = "https://production-server-eu.everafter.ai/api/v1"
        self.custom_object_id = everafter_object.get("custom_object_id", None)
        self.write_buffer = []
        self.batch_size = 1

    def _request(self, endpoint: str, http_method: str = "PUT", data: List[Mapping] = None) -> requests.Response:
        url = self.url + endpoint
        headers = {"Content-Type": "application/json", "apiKey": self.api_key}
        
        while True:
            response = requests.request(method=http_method, url=url, headers=headers, json=data)

            if response.status_code == 429:
                logger.warning(f"Rate limit hit (429) for {endpoint}. Waiting 60 seconds before retrying...")
                time.sleep(60)
                continue
            
            return response

    def get_accounts_metadata(self) -> requests.Response:
        return self._request("/accounts/metadata", "GET")

    def update_accounts(self, data: Mapping) -> requests.Response:
        account_id, data_prepared = self.clean_payload(data)
        response = self._request(
            endpoint=f"/accounts/{account_id}",
            http_method="PUT",
            data=data_prepared
        )
        if response.status_code == 404:
            logger.warning(f"Account {account_id}: {response.text}")
        elif response.status_code == 400 or response.status_code == 500:
            error_message = f"Account {account_id}: {response.text}"
            logger.error(error_message)
            raise Exception(error_message)
        else:
            return response

    def add_custom_object_records(self) -> requests.Response:
        response = self._request(
            endpoint=f"/custom-objects/{self.custom_object_id}/records/bulk",
            http_method="POST",
            data={"records": self.write_buffer}
        )
        if response.status_code == 404:
            logger.warning(f"Custom Objects {self.custom_object_id}: {response.text}")
        elif response.status_code == 400 or response.status_code == 500:
            error_message = f"Custom Objects {self.custom_object_id}: {response.text}"
            logger.error(error_message)
            raise Exception(error_message)
        else:
            return response

    def _remove_null_values(self, obj: Any) -> Any:
        """Recursively remove all elements with null values."""
        if isinstance(obj, dict):
            return {k: self._remove_null_values(v) for k, v in obj.items() if v is not None}
        elif isinstance(obj, list):
            return [self._remove_null_values(item) for item in obj if item is not None]
        else:
            return obj
    
    def clean_payload(self, data: Mapping) -> tuple[str, Mapping]:
        data_prepared = data.copy()

        if self.everafter_object == "accounts":
            key = "account_id"
            key_id = data_prepared[key]
            data_prepared.pop(key)
        else:
            key_id = None

        data_prepared = self._remove_null_values(data_prepared)

        return key_id, data_prepared

    def queue_write_operation(self, data: Mapping):
        _, data_prepared = self.clean_payload(data)
        self.write_buffer.append(data_prepared)

        if len(self.write_buffer) == self.batch_size:
            self.add_custom_object_records()
            self.write_buffer.clear()

    def main(self, data: Mapping) -> requests.Response:
        if self.everafter_object == "accounts":
            return self.update_accounts(data)
        elif self.everafter_object == "custom-objects":
            return self.queue_write_operation(data)
        else:
            raise ValueError(f"Invalid everafter_object: {self.everafter_object}")