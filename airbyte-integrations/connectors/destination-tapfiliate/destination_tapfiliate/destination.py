#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#


from typing import Any, Iterable, Mapping

from airbyte_cdk import AirbyteLogger
from airbyte_cdk.destinations import Destination
from airbyte_cdk.models import AirbyteConnectionStatus, AirbyteMessage, ConfiguredAirbyteCatalog, Status, Type

from destination_tapfiliate.tapfiliate_client import TapfiliateRestApi

class DestinationTapfiliate(Destination):
    def write(
        self, config: Mapping[str, Any], configured_catalog: ConfiguredAirbyteCatalog, input_messages: Iterable[AirbyteMessage]
    ) -> Iterable[AirbyteMessage]:

        tapfiliate_client = TapfiliateRestApi(config)
        for message in input_messages:
            if message.type == Type.STATE:
                yield message
            elif message.type == Type.RECORD:
                record = message.record
                tapfiliate_client.conversions_add_commissions_to_conversion(record.data)
            else:
                continue


    def check(self, logger: AirbyteLogger, config: Mapping[str, Any]) -> AirbyteConnectionStatus:
        """
        Tests if the input configuration can be used to successfully connect to the destination with the needed permissions
            e.g: if a provided API token or password can be used to connect and write to the destination.

        :param logger: Logging object to display debug/info/error to the logs
            (logs will not be accessible via airbyte UI if they are not passed to this logger)
        :param config: Json object containing the configuration of this destination, content of this json is as specified in
        the properties of the spec.json file

        :return: AirbyteConnectionStatus indicating a Success or Failure
        """
        try:
            tapfiliate_client = TapfiliateRestApi(config)
            response = tapfiliate_client._send_request(method='GET', end_point='conversions',parameters={'page':1})
            if response.status_code == 200:
                return AirbyteConnectionStatus(status=Status.SUCCEEDED)
            else:
                return AirbyteConnectionStatus(status=Status.FAILED, message=f"Error to get conversions status {response.status_code} : {response.content}")
        except Exception as e:
            return AirbyteConnectionStatus(status=Status.FAILED, message=f"An exception occurred: {repr(e)}")
