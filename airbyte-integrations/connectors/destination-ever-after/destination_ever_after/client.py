from typing import Any, Mapping, List
from logging import getLogger

import requests

logger = getLogger("airbyte")

class EverAfterClient():
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.url = "https://production-server-eu.everafter.ai/api/"
    
    def _request(self, endpoint: str, http_method: str = "PUT", data: List[Mapping] = None) -> requests.Response:
        url = self.url + endpoint
        headers = {"Content-Type": "application/json", "apiKey": self.api_key}
        response = requests.request(method=http_method, url=url, headers=headers, json=data)
        return response

    def get_accounts_metadata(self) -> requests.Response:
        return self._request("v1/accounts/metadata", "GET")

    def update_accounts(self, data: Mapping) -> requests.Response:
        account_id, data_prepared = self.clean_payload(data)
        response = self._request(f"v1/accounts/{account_id}", "PUT", data_prepared)
        if response.status_code == 404:
            logger.warning(f"Account {account_id} not found")
        elif response.status_code == 400:
            raise Exception(f"Account {account_id} error: {response.text()}")
        else:
            return response

    def clean_payload(self, data: Mapping) -> tuple[str, Mapping]:
        """
        Removes the 'account_id' field from data if it exists.
        Raises an error if 'account_id' is not present.
        """
        if "account_id" not in data:
            raise KeyError("Field 'account_id' is required but missing")
        
        # Extract account_id and create a copy without it
        account_id = data["account_id"]
        data_prepared = data.copy()
        data_prepared.pop("account_id")
        return account_id, data_prepared

