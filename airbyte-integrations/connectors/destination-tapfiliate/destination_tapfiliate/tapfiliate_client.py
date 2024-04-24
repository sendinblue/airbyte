import json
import time
import urllib
import requests
from logging import getLogger

logger = getLogger("airbyte")


class TapfiliateRestApi:
    def __init__(
        self,
        config,
        api_base="https://api.tapfiliate.com",
        api_version="1.6",
        retry=1,
    ):
        self.x_api_key = config['x_api_token']
        self.api_base = api_base
        self.api_version = api_version
        self.retry = retry

    def _send_request(self, method, end_point, data=None, parameters={}):
        headers = {"content-type": "application/json", "X-Api-Key": self.x_api_key}
        if parameters:
            url = f"{self.api_base}/{self.api_version}/{end_point}/?{urllib.parse.unquote(urllib.parse.urlencode(parameters))}"
        else:
            url = f"{self.api_base}/{self.api_version}/{end_point}"
        return requests.request(method= method, url= url, headers=headers, timeout=60, json=data)
    
    def _request_retry(self, response, current_retry, erreur = None):
        if current_retry < self.retry:
            logger.warning(
                f"Unexpected response status_code {response.status_code} i need to sleep 60s before retry {current_retry}/{self.retry}"
            )
            time.sleep(60)
            current_retry = current_retry + 1
            return current_retry
        else:
            if erreur:
                raise erreur
            else:
                erreur = RuntimeError(
                    f"Too many retry, status_code {response.status_code} : {response.content}"
                            )

    def get_sync_endpoints(self, end_point, parameters={}):

        if "page" not in parameters:
            parameters["page"] = 1

        is_first_call = True
        more_pages = True
        current_retry = 0

        while more_pages:
            try:
                response =  self._send_request(method='GET', end_point=end_point, parameters=parameters)
                if is_first_call:
                    logger.info(f"Get from URL (first call) : {end_point}/?page={parameters['page']}")
                else:
                    logger.debug(f"Get from URL : {end_point}/pages={parameters['page']}")

                if response.status_code != 200:
                    current_retry = self._request_retry(self, response, current_retry)
                else:
                    records = json.loads(response.content.decode("utf-8"))

                    if isinstance(records, dict):
                        records = [records]
                    for record in records:
                        yield parameters["page"], record

                    if len(records) < 25:
                        more_pages = False
                        is_first_call = False
                    else:
                        parameters["page"] = parameters["page"] + 1
                        is_first_call = False
                        
                        # The number of requests you have left before exceeding the rate limit
                        x_ratelimit_remaining = int(
                            response.headers["X-Ratelimit-Remaining"]
                        )
                        # When your number of requests will reset (Unix Timestamp in seconds)
                        x_ratelimit_reset = int(response.headers["X-Ratelimit-Reset"])

                        # if we cannot make more call : we wait until the reset
                        if x_ratelimit_remaining < 15:
                            sleep_duration = x_ratelimit_reset - time.time()
                            if sleep_duration < 30:
                                sleep_duration = 30
                            logger.warning(f"Remaining {x_ratelimit_remaining} call, I prefer to sleep {sleep_duration} seconds until the rest.")
                            time.sleep(sleep_duration)
            except Exception as e:
                current_retry = self._request_retry(self, response, current_retry, e)

    def post_sync_endpoints(self,end_point, payload):
        current_retry = 0
        while True:
            response = self._send_request(method='POST', end_point=end_point, data=payload)
            if response.status_code != 200:
                current_retry = self._request_retry(response, current_retry)
            else:
                return json.loads(response.text)

    def _validate_record(self,
        record: dict,
        required_uri_parameters,
        required_payload,
        optional_arguments,
    ):
        uri_parameters = {}
        payload = {}

        for parameter in required_uri_parameters:
            if parameter not in record.keys():
                raise KeyError(
                    f"Missing REQUIRED_URI_PARAMETERS {parameter} in {record}"
                )
            else:
                uri_parameters[parameter] = record.pop(parameter)
        
        for parameter in required_payload:
            if parameter not in record.keys():
                raise KeyError(f"Missing REQUIRED_ARGUMENTS {parameter} in {record}")
            else:
                payload[parameter] = record.pop(parameter)
        
        for parameter in optional_arguments:
            if parameter in record.keys():
                payload[parameter] = record.pop(parameter)

        return uri_parameters, payload
    

    def conversions_add_commissions_to_conversion(
        self, record: dict, filter_already_sent_commissions=True
    ):
        logger.info(f"conversions_add_commissions_to_conversion received document : {record}")
        # https://tapfiliate.com/docs/rest/#conversions-add-commissions-to-conversion
        uri_parameters, payload = self._validate_record(
            record.copy(),
            ["conversion_id"],
            ["conversion_sub_amount"],
            ["commission_type", "comment"],
        )

        if filter_already_sent_commissions:
            already_sent_commission_types = set()

            conversions = [
                conversion
                for _, conversion in self.get_sync_endpoints(
                    f"conversions/{uri_parameters.get('conversion_id')}"
                )
            ]
            if conversions is None:
                raise KeyError(
                    f"This conversion id not exists yet {uri_parameters.get('conversion_id')}"
                )
            else:
                # get all already sent commission_type
                for conversion in conversions:
                    if "commissions" in conversion:
                        for commission in conversion["commissions"]:
                            already_sent_commission_types.add(
                                commission["commission_type"]
                            )
                logger.info(f"Already sent commission_type {already_sent_commission_types} for commission id {uri_parameters.get('conversion_id')}")
            if payload.get("commission_type") in already_sent_commission_types:
                logger.info(
                    f"This commission_type {payload.get('commission_type')} already exists in this conversion {uri_parameters.get('conversion_id')}"
                )
                return True
            else:
                logger.info(
                    f"This is a new commission_type {payload.get('commission_type')} for {uri_parameters.get('conversion_id')}"
                )
        end_point = f"conversions/{uri_parameters.get('conversion_id')}/commissions/"
        response = self.post_sync_endpoints(end_point, payload)
        logger.info(f"New commission {response} added to conversion {uri_parameters.get('conversion_id')}")
        return True