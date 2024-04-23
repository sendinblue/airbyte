#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#


from logging import getLogger
from typing import Any, Iterable, Mapping

from airbyte_cdk import AirbyteLogger
from airbyte_cdk.destinations import Destination
from airbyte_cdk.models import AirbyteConnectionStatus, AirbyteMessage, ConfiguredAirbyteCatalog, Status, Type
from destination_google_ads.google_ads_handler import GoogleAdsHandler

logger = AirbyteLogger()

API_VERSION = "v15"


class DestinationGoogleAds(Destination):
    def write(
        self, config: Mapping[str, Any], configured_catalog: ConfiguredAirbyteCatalog, input_messages: Iterable[AirbyteMessage]
    ) -> Iterable[AirbyteMessage]:

        client = GoogleAdsHandler(config)
        for message in input_messages:
            if message.type == Type.STATE:
                yield message
            elif message.type == Type.RECORD:
                client.queue_batch(message.record.data)
        if len(client.write_batch) > 0:
            client.flush()

    def check(self, logger: AirbyteLogger, config: Mapping[str, Any]) -> AirbyteConnectionStatus:

        try:
            GoogleAdsHandler(config).get_customers()
            return AirbyteConnectionStatus(status=Status.SUCCEEDED)
        except Exception as e:
            return AirbyteConnectionStatus(status=Status.FAILED, message=f"An exception occurred: {repr(e)}")
