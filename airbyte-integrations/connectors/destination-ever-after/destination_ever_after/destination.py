#
# Copyright (c) 2025 Airbyte, Inc., all rights reserved.
#

from logging import Logger, getLogger
from typing import Any, Iterable, Mapping

from airbyte_cdk.destinations import Destination
from airbyte_cdk.models import AirbyteConnectionStatus, AirbyteMessage, ConfiguredAirbyteCatalog, Status, Type
from destination_ever_after.client import EverAfterClient


logger = getLogger("airbyte")

class DestinationEverAfter(Destination):
    def write(
        self, config: Mapping[str, Any], configured_catalog: ConfiguredAirbyteCatalog, input_messages: Iterable[AirbyteMessage]
    ) -> Iterable[AirbyteMessage]:
        client = EverAfterClient(**config)
        for message in input_messages:
            if message.type == Type.RECORD:
                record = message.record
                client.main(record.data)
            elif message.type == Type.STATE:
                yield message
            else:
                continue
        
        if len(client.write_buffer) != 0 and client.everafter_object == "custom-objects":
            client.add_custom_object_records()


    def check(self, logger: Logger, config: Mapping[str, Any]) -> AirbyteConnectionStatus:
        try:
            client = EverAfterClient(**config)
            response = client.get_accounts_metadata()
            if response.status_code != 200:
                raise Exception("Failed to get accounts metadata")
            else:   
                return AirbyteConnectionStatus(status=Status.SUCCEEDED)
        except Exception as e:
            return AirbyteConnectionStatus(status=Status.FAILED, message=f"An exception occurred: {repr(e)}")
