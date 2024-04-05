import base64
import requests
from typing import Any, Mapping, List


class UserpilotClient:
    def __init__(self, api_key: str, uobject: str) -> None:
        self.api_key = api_key
        self.endpoint = uobject.get("endpoint")

    def _get_base_url(self) -> str:
        return f"https://analytex.userpilot.io/v1/{self.endpoint}"
    
    def _get_auth_headers(self) -> Mapping[str, Any]:
        return {
                'Authorization': f'Token {self.api_key}',
                'X-API-Version': '2020-09-22',
            }
    
    def _request(self, http_method: str = "POST", data: List[Mapping] = None) -> requests.Response:
        url = self._get_base_url()
        headers = {"Content-Type": "application/json", **self._get_auth_headers()}
        response = requests.post(method=http_method, url=url, headers=headers, json=data)
        return response
    
    
    def validate_data(self, data: List[Mapping]):
        validated_data = {}
        if self.endpoint == "identify":
            if not data.get('user_id'):
                raise Exception("User_id is required for identify endpoint")
            else:
                validated_data['user_id'] = data.get('user_id')
            if data.get('metadata'):
                validated_data['metadata'] = data.get('metadata')
            if data.get('company'):
                validated_data['company'] = data.get('company')
        return validated_data

    def write(self, request_body: List[Mapping]):
        validated_data = self.validate_data(request_body)
        return self._request(data=validated_data)
