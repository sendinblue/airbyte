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

    def add_custom_object_records(self, data: Mapping) -> requests.Response:
        custom_object_id, data_prepared = self.clean_payload(data)

        response = self._request(
            endpoint=f"/custom-objects/{custom_object_id}/records",
            http_method="POST",
            data=data_prepared
        )
        if response.status_code == 404:
            logger.warning(f"Custom Objects {custom_object_id}: {response.text}")
        elif response.status_code == 400 or response.status_code == 500:
            error_message = f"Custom Objects {custom_object_id}: {response.text}"
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
        if self.everafter_object == "accounts":
            key = "account_id"
        else:
            key = "custom_object_id"

        if key not in data:
            raise KeyError(f"Field '{str(key)}' is required but missing")

        key_id = data[key]
        data_prepared = data.copy()
        data_prepared.pop(key)
        
        data_prepared = self._remove_null_values(data_prepared)
        
        return key_id, data_prepared

    def main(self, data: Mapping) -> requests.Response:
        if self.everafter_object == "accounts":
            return self.update_accounts(data)
        elif self.everafter_object == "custom-objects":
            return self.add_custom_object_records(data)
        else:
            raise ValueError(f"Invalid everafter_object: {self.everafter_object}")