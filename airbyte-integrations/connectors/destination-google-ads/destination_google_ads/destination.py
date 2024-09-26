#
# Copyright (c) 2024 Airbyte, Inc., all rights reserved.
#

import logging

from typing import Any, Iterable, Mapping

from airbyte_cdk.destinations import Destination
from airbyte_cdk.models import AirbyteConnectionStatus, AirbyteMessage, FailureType, ConfiguredAirbyteCatalog, Status, Type
from airbyte_cdk.utils import AirbyteTracedException

from destination_google_ads.google_ads_handler import GoogleAdsHandler
from destination_google_ads import google_ads_offline_conversion



class DestinationGoogleAds(Destination):
    def write(
        self, config: Mapping[str, Any], configured_catalog: ConfiguredAirbyteCatalog, input_messages: Iterable[AirbyteMessage]
    ) -> Iterable[AirbyteMessage]:

        client = GoogleAdsHandler(config)
        data = []
        batch_size = 500

        conversion_handler = getattr(
            google_ads_offline_conversion, config["offline_conversion"]
        )

        for message in input_messages:
            if message.type == Type.STATE:
                yield message
            elif message.type == Type.RECORD:
                message = message.record.data
                if message.get("conversion_id") is None:
                    raise AirbyteTracedException(
                        message="No conversion id",
                        internal_message="Failed to send conversion. A conversion id is required.",
                        failure_type=FailureType.config_error,
                    )                    
                else:
                    record = client.write_message(conversion_handler, message)
                    data.append(record)
                    if len(data) >= batch_size:
                        client.send_data(data)
                        data = []

        if len(data) > 0:
            client.send_data(data)

    def check(self, logger: logging.Logger, config: Mapping[str, Any]) -> AirbyteConnectionStatus:
        try:
            GoogleAdsHandler(config).get_customers()
            return AirbyteConnectionStatus(status=Status.SUCCEEDED)
        except Exception as e:
            return AirbyteConnectionStatus(status=Status.FAILED, message=f"An exception occurred: {repr(e)}")
