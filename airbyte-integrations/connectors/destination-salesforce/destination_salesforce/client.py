import requests
from typing import Any, Mapping
from simple_salesforce import Salesforce, SalesforceExpiredSession

from airbyte_cdk.utils import AirbyteTracedException
from airbyte_protocol.models import FailureType


AUTHENTICATION_ERROR_MESSAGE_MAPPING = {
    "expired access/refresh token": "The authentication to SalesForce has expired. Re-authenticate to restore access to SalesForce."
}

class SalesforceClient:
    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        refresh_token: str = None,
        is_sandbox: bool = None,
        sobject: str = 'Account',
        batch_size: int = 10000
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.sobject = sobject
        self.is_sandbox = is_sandbox
        self.batch_size = batch_size
        self.instance = None
        self.instance_url = ""
        self.access_token = None
        self.write_buffer = []

    def generate_token(self):
        login_url = "https://login.salesforce.com/services/oauth2/token"
        login_body = {
            'grant_type': "refresh_token",
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token
        }
        resp = requests.post(url=login_url, data=login_body)
        return resp.json()

    def login(self):
        auth = self.generate_token()
        self.access_token = auth['access_token']
        self.instance_url = auth['instance_url']

        if self.is_sandbox:
            sf = Salesforce(instance_url= self.instance_url, session_id= self.access_token, domain='test')
        else:
            sf = Salesforce(instance_url= self.instance_url, session_id= self.access_token)

        self.instance = sf

    def describe(self):
        sf = self.instance
        try:
            resp = sf.query(f"SELECT Id FROM {self.sobject}")
        except Exception as e:
            raise Exception(f"not found a description for the sobject '{self.sobject}'")


    def transform(self, record: Mapping):
        record = {k: v for k, v in record.items() if v is not None}
        return record


    def queue_write_operation(self, record: Mapping):
        data = self.transform(record)
        self.write_buffer.append(data)
        if len(self.write_buffer) == self.batch_size:
            self.flush()


    def flush(self):
        print(self.write_buffer)
        try:
            sf = self.instance
            getattr(sf.bulk, self.sobject).upsert(data = self.write_buffer, external_id_field = 'Id', batch_size = self.batch_size, use_serial=True)
        except SalesforceExpiredSession as err:
            if err.response.status_code == requests.codes.BAD_REQUEST:
                if error_message := AUTHENTICATION_ERROR_MESSAGE_MAPPING.get(err.response.json().get("error_description")):
                    self.login()
        except Exception as e:
            raise AirbyteTracedException(message=e, failure_type=FailureType.config_error)




